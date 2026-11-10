# Repayment Resilience: product requirements and test plan

My own proposal, written as a case study. Not based on any company's internal data or documents.

## The problem

Some customers may have a due date that lands just before payday. If so, the debit can fail, a fee follows, and they start falling behind for a reason that has little to do with whether they can afford the loan. How often this happens is the first thing to check in real data. Other customers really can't afford their payments anymore, and what they need is a person and a realistic plan, not more credit.

The goal is more on-time payments and fewer accounts sliding into collections, without hiding losses or making anyone's situation worse.

## Who this is for

1. People with steady income and the wrong timing. They can pay, the date just doesn't match their payday, and they need an easy, clearly explained way to move it.
2. People in temporary hardship: job loss, illness, a gap in income. They need someone to look at what they can afford and agree a plan.
3. The recoveries team. They need one clear record per customer: eligibility, payment attempts, consent and what was agreed.

## Phase 1 scope

- A due-date change option in the account, available when the customer is eligible (payday evidence, autopay in place, within the allowed window).
- A preview before confirming: new date, amount, any fee or interest effect, and how to undo it.
- A hardship request form that goes to a person for an affordability review. Nothing is auto-approved.
- Event tracking from eligibility through to payment result, failures and complaints.
- An audit log of who changed what, when, and with what consent.
- A feature flag so it can be switched off quickly if payments start failing.

Not in Phase 1: new loans of any kind, automated hardship approvals, and automatic credit bureau changes.

## Test design

Randomize by customer. If someone has more than one account, all of them go in the same group.

Eligible customers have a due date more than 4 days from payday, are current to 30 days behind, have the required consents, and aren't on another hardship plan. Control keeps today's experience; treatment gets the option to align the due date to payday. I'd track how many actually take the option, but analyze everyone as assigned.

The decision measure is the share of first payments collected by day 60 after assignment, plus dollars collected per customer by then. It's on a fixed calendar because moving the due date moves the finish line for "on time". On-time against the customer's own due date and collection by day 30 are supporting measures. I'd also watch cure and roll rates at 30, 60 and 90 days, collections activity and retention.

Stop signals: complaints, NSF fees, later missed payments, accounts rolling further behind, consent reversals, and anything suggesting vulnerable customers do worse.

Sample size is planned on the decision measure. At the simulated 90.4% day-60 baseline, 5% significance and 80% power, that's about 1,300 customers per group for a 3-point lift (3,085 for 2 points, 404 for 5). Sizing on on-time at a 72% baseline would need 3,395 per group for 3 points, so the choice of measure matters. Before picking a run time, check how many eligible customers arrive each month, and allow for drop-outs and repeated looks.

Roll out only with a credible lift on the decision measure, no meaningful harm on the stop signals, and policy and legal sign-off.

## Hardship assistance (Phase 1)

A customer reports hardship, or keeps missing payments. In the demo I route people 15 to 59 days behind who report hardship, but that window is a starting assumption, not a rule. A person reviews income, essential costs and other debts, then can offer a lower temporary payment, a new due date or a structured plan, with the terms explained and agreed. Success means the customer gets back on track and stays there, without complaints.

## Phase 2: hardship and settlement loans

The question here is whether new lending can sometimes help someone more than adjusting the existing loan. I'd only go there after modification options are exhausted, and only where the new terms are clearly more affordable once total cost is compared.

For a hardship loan, decide APR, fees, term, how it's reported to the bureaus, how it's adjudicated and how servicing handles it, before anything launches.

For settlements, there's a difference between accepting a reduced amount on the existing debt and lending someone money to pay a settlement. Neither is automatically better for the customer.

Three numbers, with different denominators:

- acceptance rate = accepted offers / offers made
- completion rate = completed settlements / accepted offers
- overall recovery = what the whole offered group pays back

The decision rule, for a customer who accepts:

```
With settlement    = completion rate x (settlement amount - completion cost)
                   + (1 - completion rate) x (recovery if it fails - extra collections cost)
                   - setup cost
Without settlement = expected recovery through normal collections
```

Offer a settlement only if the first is higher than the second, and the customer can afford it and has been treated fairly. The acceptance rate doesn't change whether the offer wins for each customer who accepts; it changes how many customers it reaches and so the total. Because everything hinges on completion, `src/settlement_breakeven.py` works out the break-even completion rate for a range of discounts and collections recoveries. Costs are split by when they happen: setup on acceptance, a cost on completion, and extra collections work on failure. With 1%, 2% and 2% of the balance, a 50% settlement against 25% expected collections needs more than about 27% of accepted settlements to complete; charging cost only on completion would wrongly lower that to about 19%. Credit Risk would need to estimate collections recovery for the customers who accept, not the average account, since acceptors may be the ones who would have paid anyway. The launch test should compare overall recovery for everyone offered against a group not offered a settlement.

Sign-off would come from the Group PM for Credit, Credit Risk, Finance, Legal and Compliance, any partner bank, Engineering and Data, Collections Operations and Customer Support, and Privacy.

Before launch there need to be contracts with version control, correct ledger and fees, delinquency logic, hardship flags, bureau reconciliation, a way to pause and resume collections, agent overrides with a reason code, a dispute process and rollback. I'd start with manual approvals and a capped pilot.

## On-load collections

Collecting part of an overdue payment when money is loaded can lift recoveries. It can also take money someone needed for rent or food. If it's tested at all: explicit consent with clear notice, a conservative cap, exemptions for hardship, fast reversal when there's a dispute, and partner and legal approval. Randomize by customer, judge it on net recoveries alongside complaints, hardship referrals and later missed payments, and stop if customers are being hurt.

## Measuring the money

Without real charge-off data I don't estimate savings. With real data I'd start from losses avoided:

```
(control charge-off roll rate - treatment charge-off roll rate) x balance at risk x loss rate at charge-off
```

measured on comparable cohorts over a horizon set in advance. Gross profit would also need revenue, funding, servicing and build costs, agreed with Finance and Credit Risk.

## Risks and dependencies

Who the legal lender is and which rules apply; whether servicing can change terms without new underwriting; disclosures and valid consent; payment rail failures and duplicate debits; credit bureau accuracy; provincial collections rules; privacy of income data; fair outcomes across customer groups.

## Order of work

Check the baseline and eligible volume; confirm policy, legal and risk feasibility; finish UX and sign the PRD; build tracking and test it; run a small opt-in pilot; run the registered test; review results and complaints; then roll out in stages or roll back.
