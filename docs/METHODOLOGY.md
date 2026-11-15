# Methodology

CyberCheckup is a *control-based* self-assessment. It asks whether common, well-understood protections are in place and ranks the gaps by how much they matter and how hard they are to fix.

## 1. Controls
Each of the 37 questions is one control, grouped into nine areas. They are chosen from the failures that most often hurt small businesses: account takeover, phishing and payment fraud, ransomware and lost data, lost or stolen devices, weak Wi-Fi, careless handling of personal data, and slow response. The wording is plain on purpose: a shop owner should be able to answer without a technical helper.

## 2. Ratings
| Field | Scale | Meaning |
|---|---|---|
| Impact | 1-5 | Harm to the business if the control is missing |
| Likelihood | 1-5 | How often small businesses are actually hit through this gap |
| Effort | 1-3 | 1 under an hour and usually free, 2 about a day or a small cost, 3 a project |

These are judgement-based ratings, set from public incident patterns and practitioner experience. They are not measured probabilities. Edit them in `questions.yaml` if your context differs, and say so in your report.

## 3. Scoring
```
gap            = 1 - value          value: yes 1.0, partly 0.5, no 0.0, not sure 0.0
max risk       = likelihood x impact x sector weight
risk           = max risk x gap
area score     = 100 x (1 - sum(risk) / sum(max risk))      over answered controls in that area
overall score  = same formula across all applicable controls
```
Controls answered "not applicable", and controls that do not apply to the business (for example staff-offboarding questions for a one-person business), are left out of both sums. Unanswered questions count as "not sure".

## 4. Sector weights
A sector multiplies the risk of every control in an area. A clinic's data-area controls are weighted 1.5 because patient records are sensitive and regulated. A shop's payments controls are weighted 1.4 because mobile money and card fraud hit retail hardest. Weights are listed in `profiles.yaml`.

## 5. Prioritisation
1. **Fix first:** risk of 18 or more (for example, a missing control with likelihood 5, impact 4 and no sector weight scores 20).
2. Remaining gaps are grouped by effort into **this week**, **this month** and **this quarter**.
3. Inside each group the highest risk comes first.

The aim is "most risk removed for the least effort", so an owner with one free afternoon knows what to do.

## 6. Bands
80 or more is Healthy, 60 to 79 Fair, 40 to 59 At risk, below 40 Needs urgent attention. The bands help conversation, but the ranked action list is the real product.

## 7. Known limitations
* Answers are self-reported and can be optimistic. Where possible, check them (open the router page, look at the backup).
* Ratings are judgement-based and sector weights are coarse.
* The tool does not test systems and finds no vulnerabilities in software.
* The data protection items name Kenya's regulator. Adapt them for other countries.
