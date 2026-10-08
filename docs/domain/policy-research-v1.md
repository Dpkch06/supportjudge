# Dropbox source verification

I used the installed research skill and checked first-party Dropbox help articles on 2026-10-07. The dataset uses checked paraphrases, not quotations or user-forum claims. Its labels remain AI-authored provisional judgments.

| Family | Verified rule and source |
| --- | --- |
| Cancellation | Plus cancellation takes effect at billing-cycle end. App deletion and card expiry do not cancel billing. Basic quota restrictions can include later file deletion. [Individual cancellation](https://help.dropbox.com/plans/downgrade-dropbox-individual-plans) |
| Refund | Payments generally are not refundable. The EU, UK, and Turkey exception covers Plus cancellation within 14 days. Storefront and direct-debit cases have different routes. [Refunds](https://help.dropbox.com/plans/refund) |
| Billing | Credit-card lookup uses a transaction ID and does not cover PayPal or other methods. Banks can transfer billing to a replacement card. [Charge lookup](https://help.dropbox.com/billing/find-credit-card-charge) |
| Recovery | Basic and Plus standard recovery is 30 days, with possible add-on extensions. Permanent deletion is outside recovery, shared restoration needs editing permission, and support must not receive login codes. [Deleted-file recovery](https://help.dropbox.com/delete-restore/recover-deleted-files-folders) |
| Account access | Knowing the password, having a verified recovery email, or an eligible linked-device flow affect recovery. Dropbox cannot recover the mailbox or replace account email on request. [Lost email access](https://help.dropbox.com/account-access/lost-email-access) |
| Support | Basic and Plus have different channels. Plus has no phone entitlement, uses the assistant before email or chat, and has stated business-hour limits. [Support options](https://help.dropbox.com/account-settings/customer-support-levels) |

## Decisions

Use Basic and Plus because the rules offer concrete comparisons that teammates can verify. Do not import team-only phone support or professional-plan recovery periods into individual cases. Treat dates, location, purchase channel, and account permissions as inputs rather than assumptions.

Avoid claiming cancellation protects all files forever. The current cancellation article explicitly describes possible deletion for accounts that remain over quota. Avoid a blanket worldwide 14-day refund rule. Avoid promising restoration after permanent deletion or assigning Plus round-the-clock phone support.

All same-family cases stay in one split. Articles can change, so the manifest records evidence hashes and retrieval dates. The generator must be updated deliberately when policy changes; fetching fresh pages at evaluation time would make historical runs harder to reproduce.

## Coverage still needed

A human review pass should check especially the account-recovery conditions, which distinguish an expired password from a forgotten password. Real support conversations, multilingual requests, subtle partial correctness, and less obvious judge attacks are future additions. The current set checks a working pipeline and does not establish production quality.
