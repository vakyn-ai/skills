---
tags: [vakyn-questions]
runs: 1
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

We hire for four roles: backend engineer, frontend engineer, designer and data analyst. Each job
application comes in as a form (name, the role they applied for, a list of past jobs with start and
end dates, a yes/no field "has work permit") plus a free-text cover letter. For each application I
want to know:

- which of our four roles the person really fits, whatever they applied for;
- whether they have more than 5 years of work experience in total;
- how good the cover letter is;
- whether the cover letter mentions both salary expectations and willingness to relocate;
- a short, friendly rejection email for the people we turn down.

How should I ask VAKYN each of these? I don't need code yet, just which question type for each and why.
