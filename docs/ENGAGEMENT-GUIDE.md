# Running an assessment with a real business

A good session takes 45 to 60 minutes. The owner learns what to do first, and you learn what the questions miss.

## Before you start
1. **Get written consent.** Explain what you will ask, what the output contains, who will see it, and that it can be deleted on request. A short signed note is enough.
2. **Agree the scope.** This is an interview. Do not log in to systems, test the network, or look at customer data without separate written permission.
3. **Ask the owner to join**, and one staff member who handles money or customer details if there is one.

## During the session
* Read each question aloud in your own words, and use `?` to explain why it matters.
* Where you can, **check rather than ask**: ask them to show the router sticker, the phone's lock settings, the backup drive. Record the honest answer, even if it is "no".
* Do not shame anyone. "Not sure" is a useful answer.

## After the session
1. Run `cybercheckup assess` (or `--answers`) and open `report.html` together. Walk through **Start here** and the *Fix first* actions only.
2. Agree three actions with owners and dates, using `action-plan.csv`.
3. Offer to run the 30-minute staff briefing from `staff-briefing.html`.
4. Book a follow-up in about three months, then run `cybercheckup compare` to show progress.

## Handling the data
* `assessment.json` and `report.html` describe the business's weaknesses. Hand the folder to the owner, then delete your copies unless they ask you to keep them.
* Do not publish a business's report, even with the name removed, without permission.
* If you notice an active compromise (unknown payments, a hijacked account), stop the assessment and help them follow the incident response plan first.
