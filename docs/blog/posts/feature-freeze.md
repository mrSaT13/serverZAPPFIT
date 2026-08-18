---
draft: false 
date: 2026-05-23
authors:
  - joaovitoriasilva
categories:
  - Project update
  - Maintenance
---

# Pausing new features so Endurain can keep growing

Endurain has grown a lot since it started as a personal self-hosted fitness tracking project. It now supports multiple users, activity imports, Strava and Garmin integrations, privacy controls, goals, notifications, MFA, password reset flows, SSO support, translations, and more.

That growth is a good thing. It means the project is useful to more people and is solving real problems for self-hosted fitness tracking. But it also means the codebase has reached a point where adding more features without first strengthening the foundations would make the project harder to maintain over time.

For that reason, I am putting Endurain into a temporary feature freeze.

This does not mean the project is paused. It means the focus is shifting from adding visible features to making the existing project stronger, easier to maintain, and safer to evolve.

<!-- more -->

## Why this is needed

Some parts of Endurain grew organically as features were added. That is normal for a young project, especially one maintained mostly by one person in spare time. But as more integrations, authentication flows, background tasks, and user-facing features were added, a few areas became harder to change safely.

The main issue is not that Endurain needs to be rewritten. It does not. The project has a good foundation (I think) and a lot of working functionality. The issue is that some internal boundaries need to become clearer before the next wave of features can be added responsibly.

A few examples of the kind of work this freeze will focus on:

- Making authentication and user profile code easier to reason about.
- Separating responsibilities between modules more clearly.
- Reducing process-local state that can behave inconsistently in some deployments.
- Making scheduled and background work more predictable.
- Improving the reliability of imports, syncs, and maintenance tasks.
- Making the codebase easier for contributors to understand and review.
- Keeping pull requests smaller, safer, and focused on one concern at a time.

## What the feature freeze means

During the freeze, I will pause work on large new features and focus on refactoring, reliability, tests, and documentation.

The following work will continue:

- Security fixes.
- Bug fixes.
- Small compatibility fixes.
- Documentation improvements.
- Translation work.
- Maintenance updates.
- Refactor pull requests that improve the codebase without changing behavior.
- Add tests, linting, and formatting.
- Improve CI/CD checks and release confidence.

The following work will generally wait until after the freeze:

- Large new user-facing features.
- New major integrations.
- Big UI additions.
- New social features.
- Feature work that depends on backend areas currently being refactored.

This is not meant to block community participation. You can still contribute on the actions above!

Endurain remains a self-hosted fitness tracking service.

The goal is still to give users control over their data, their deployment, and their fitness history. The project remains community-oriented, and focused on privacy-conscious self-hosting.

## How the work will be done

The refactor work will be split into small, reviewable steps. I want to avoid large pull requests that are difficult to understand, test, or review.

The general approach will be:

- Open issues before larger refactors.
- Keep pull requests focused on a single concern.
- Avoid behavior changes when a pull request is meant to be a pure refactor.
- Add or update tests where the risk justifies it.
- Document new internal boundaries as they become stable.
- Keep the project usable throughout the process.

I will try to share progress as the work moves forward, especially when important refactors are completed. I will not promise a date for this because, well, there is life and a lot can happen between today and tomorrow.

## How can you help

There are several useful ways to help during this period:

- Test releases and report regressions.
- Review small refactor pull requests.
- Improve documentation where something is unclear.
- Help with translations through Codeberg Translate.
- Open issues for bugs with clear reproduction steps.
- Discuss larger changes before starting implementation work.

If you were planning a larger feature contribution, please open an issue first so we can decide whether it should wait until the relevant refactor work is complete.

## Thank you note

Thank you to everyone who uses, tests, reports issues, translates, sponsors, or contributes to Endurain.

## Newsletter

--8<-- "_snippets/newsletter.html"
