---
draft: false
date: 2026-06-18
authors:
  - joaovitoriasilva
categories:
  - Project update
  - Maintenance
---

# Feature freeze update 2

This is the second update on feature-freeze progress. Before I start, have you already subscribed to Endurain's [newsletter](#newsletter) powered by [Keila](https://keila.io)? If not, you can subscribe to it at the end of this blog post.

To start let me introduce the new Endurain release cycle. We are aiming to a monthly release, targeting the 3rd Wednesday of each month, where we can skip a release if necessary. An example of this is the month of August, where typically things slow down with holidays. Yesterday was the 3rd Wednesday of the month, however we did not release an official release this month. Instead we are releasing a beta version. Possibly we will release a beta each week until next month so we can get feedback if we are breaking something on all the refactoring we are doing. These releases will almost certainly have bugs and regressions so backup before upgrading.

On the next release (and beta versions until then) you'll notice a new login screen image if using the default one. Fun fact, this was a bikepacking weekend that myself and Hugo did a few years ago and this image seemed perfect to celebrate Hugo joining the project.

We are exploring launching official Endurain gear to help us promote and support the project. We have nothing defined yet, but we would like your feedback on it. You can give your feedback in this [form](https://forms.office.com/r/VHxLtdkMVj).

We created a new bot account `pacer-bot` and we will start automating some things.

<!-- more -->

## Development updates

We continue the work on the backend, and the following changes were to it.

In the latest weeks we focused on reducing the supply chain attack surface, which is a hot topic at the moment. This work builds on the runtime security improvements started in the previous cycle, ensuring Docker containers no longer run as root, with proper permission handling for volumes.

Many Endurain instances run in homelab environments, and we take seriously the responsibility of making sure that common attack vectors don't reach your homelab through Endurain's stack. Our approach combines host-level hardening with supply chain defenses:

- We now use version pinning, using SHAs and specific version on external dependencies (actions, uv, etc) [#670](https://codeberg.org/endurain-project/endurain/pulls/670) and [#688](https://codeberg.org/endurain-project/endurain/pulls/688).
- Dependencies with less than 30 days are not installed. This means we give at least 30 days to someone find some vulnerability before letting it in on Endurain's logic [#689](https://codeberg.org/endurain-project/endurain/pulls/689).

Following the work of linting and formatting, we now also enforce passing tests and at least 80% coverage [#658](https://codeberg.org/endurain-project/endurain/pulls/658).

We finished the auth module refactor [#625](https://codeberg.org/endurain-project/endurain/issues/625), and we did a lot of tests to make sure nothing breaks and nothing changes at the behaviour level, however regressions may happen and your usage will help us understand if anything broke. Finally a short summary of why was this important:

- **Single ownership reduced risk**: Before, auth logic was spread across multiple places, which made it easier for rules to drift. Consolidating under one auth boundary means there is now one clear source of truth for login, sessions, MFA, SSO, API keys, and step-up checks.
- **Security controls became consistent**: Critical protections now apply in a predictable way across flows.
- **Attack surface got smaller**: Centralizing auth internals and enforcing boundaries reduced accidental direct access to low-level modules. Fewer bypass paths means fewer chances for subtle auth bugs.
- **Safer evolution of features**: When auth rules are centralized, adding or changing features (new client flows, IdP behavior, API key policies, step-up requirements) is lower-risk because changes happen in one place instead of many.
- **Better observability and auditing**: A coherent auth layer improves logging and incident response. It becomes easier to answer: `What happened, why was access granted, and where should we fix it?`. We will have to build on top of this, but the foundation is there.
- **Less regression-prone for contributors**: Refactors like this are not just security work, they’re maintainability work. New contributors can reason about auth behavior faster, and tests become more meaningful because they validate one architecture, not scattered special cases.
- This work also identified some small issues, both at the functional and security level that should be fixed.

We are now simultaneously doing the activity ingestion refactoring, enforcing ORM objects (models) do not leave CRUD logic and enforcing mypy typecheck:

- mypy typecheck will make the code safer so we can refactor faster [#700](https://codeberg.org/endurain-project/endurain/pulls/700).
- ORM objects are a pain because if you edit them you can commit those edits to the database without knowing it and when it was not supposed to happen. So using ORM objects outside CRUD logic (where they are in fact needed) is now prohibited [#704](https://codeberg.org/endurain-project/endurain/pulls/704).
- On activity ingestion:
  - Like you may be aware, there are a lot of things that currently happen in the API thread, breaking/stopping/slowing the API requests and this results on a poor experience for the user because the UX gets unresponsive [#693](https://codeberg.org/endurain-project/endurain/pulls/693) and [#700](https://codeberg.org/endurain-project/endurain/pulls/700).
  - Some static things are being computed on every request which does not make sense, so we are converting them to be calculated and stored at ingestion [#693](https://codeberg.org/endurain-project/endurain/pulls/693) and [#700](https://codeberg.org/endurain-project/endurain/pulls/700).

We also fixed some issues along the way [#663](https://codeberg.org/endurain-project/endurain/pulls/663), [#667](https://codeberg.org/endurain-project/endurain/pulls/667), [#668](https://codeberg.org/endurain-project/endurain/pulls/668), [#669](https://codeberg.org/endurain-project/endurain/pulls/669), [#692](https://codeberg.org/endurain-project/endurain/pulls/692), [#708](https://codeberg.org/endurain-project/endurain/pulls/708), [#709](https://codeberg.org/endurain-project/endurain/pulls/709) and [#710](https://codeberg.org/endurain-project/endurain/pulls/710).

## Thank you note

Thank you to everyone who uses, tests, reports issues, translates, sponsors, or contributes to Endurain.

## Newsletter

--8<-- "_snippets/newsletter.html"
