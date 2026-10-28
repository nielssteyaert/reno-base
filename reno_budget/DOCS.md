# Renovation Budget

Track the budget of your home renovation from the Home Assistant sidebar: expenses from estimate to
paid, installments, categories and rooms with their own budgets, milestones, reports and Excel
export.

## Getting started

1. Open **Renovation** in the sidebar.
2. In **Settings**, enter your **total budget** (incl. VAT) and a **contingency reserve** (e.g. 10%).
   Check the VAT rates: in Belgium, renovating a home older than 10 years is usually 6%, otherwise 21%.
3. Create **categories** (e.g. Electrical, Kitchen › Cabinets) and **rooms**. Both can have their own
   budget; leave a budget empty if you don't want to track it at that level.
4. Add **expenses**, or **import** an existing spreadsheet.

## How the numbers work

Every expense has an amount and a VAT rate. You can type the amount excluding or including VAT; the
other is calculated. All budgets and reports use amounts **including VAT**, because that is what you
pay.

An expense moves through these stages:

| Stage | Meaning | Counted as |
| --- | --- | --- |
| Estimate | Your own guess | Estimated |
| Quote | A supplier's quote you haven't accepted yet | Quoted |
| Ordered | You've signed or ordered | Committed |
| Invoiced | You've received the invoice | Committed |
| Paid | Payments cover the full amount (set automatically) | Committed and paid |

An expense with any payment counts as committed, whatever its stage.

- **Forecast** (projected final cost) = committed + quoted + estimated.
- **Outstanding** = committed but not paid yet.
- **Remaining** = budget − forecast.
- The **contingency reserve** sits inside the total budget. The working budget is the total minus
  the reserve. The dashboard warns when the forecast eats into the reserve, and again when it exceeds
  the total budget.
- A category's spending includes its subcategories. A category without its own budget uses the sum
  of its subcategories' budgets.
- Status labels: **On track** (below 90% of budget), **Near budget** (90–100%), **Over budget**.

## Payments

Open an expense and go to **Payments** to record installments (deposit, interim, final). **Pay
remaining** records one payment for whatever is still open. Once the payments cover the total, the
expense shows as **Paid**.

## Files

Attach quotes, invoices and photos (max 25 MB each) under **Files** on an expense. They are stored
in the app's data folder and included in backups.

## Import

**Import** reads `.xlsx` and `.csv` files. Column names in English and Dutch are recognised (e.g.
*Omschrijving*, *Bedrag*, *BTW*, *Categorie*, *Leverancier*, *Datum*, *Betaald*). You can:

- choose whether the amounts in the file include VAT;
- map each column yourself;
- decide for each unknown category, room or supplier whether to create it or map it to an existing
  one;
- review every row before importing. Rows with errors are skipped.

Write subcategories as `Kitchen > Cabinets` in the category column, or use a separate Subcategory
column. Download the template from the Import page for the full list of columns.

## Export to Excel

- **Reports → Full workbook**: summary, expenses, payments, categories, rooms, suppliers, milestones
  and monthly figures in one workbook, with filters, totals and charts.
- **Reports → Export report**: only the report you are looking at.
- **Expenses → Excel**: exactly the expenses currently shown in the table, after filters.

## Backups

**Backups** creates a zip with the database and all attached files. You can download it, restore it,
or restore from a zip on your computer. Before a restore, a safety backup of the current state is
made automatically.

Home Assistant's own backups also include this app's data. The app stops briefly during them, so
the database is always consistent.

## History

Every change is logged with the Home Assistant user who made it. Open **History** for everything, or
the **History** tab of an expense for that expense, its payments and its files.

## Configuration

| Option | Default | Description |
| --- | --- | --- |
| `log_level` | `info` | How much the app logs. |
| `auto_backup` | `true` | Create a backup every night at 03:00. |
| `backup_keep` | `14` | Number of nightly backups to keep. Manual backups are never removed automatically. |

## Data and privacy

Everything stays on your Home Assistant machine in the app's `/data` folder. The app is only
reachable through Home Assistant's ingress (the sidebar panel) and makes no outside connections.
