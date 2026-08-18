---
draft: false
date: 2026-06-02
authors:
  - joaovitoriasilva
categories:
  - Project update
  - Maintenance
---

# Feature freeze update 1

This is the first update on feature-freeze progress. To be honest, I do not have much to share development-wise, but since I have a new toy, the new [newsletter](#newsletter) powered by [Keila](https://keila.io), I had to use it. You can subscribe to it at the end of this blog post.

The newsletter will mirror, at least for now, the blog posts, and this may change in the future.

Before jumping into the development updates, we will stop framing work as `I did this...` or `I decided this...` and use `We did this...` and `We decided this...` instead. Please welcome [Hugo](https://codeberg.org/hugobatista) as a project member! 🎉 You may have already seen some commits, PRs, issues, comments, etc. done by him.

<!-- more -->

## Development updates

One of the first things we are tackling is making it easier for someone who has just discovered the project to quickly start an instance. Some new defaults are in place, and we made a few tweaks so fewer settings need to be changed and spin-up is easier and faster ([#613](https://codeberg.org/endurain-project/endurain/pulls/613), [#615](https://codeberg.org/endurain-project/endurain/pulls/615) and [#618](https://codeberg.org/endurain-project/endurain/pulls/618)).

Hugo spent the last week working on linting and formatting the codebase, and we now enforce workflows that run those checks before any merge ([#628](https://codeberg.org/endurain-project/endurain/pulls/628), [#630](https://codeberg.org/endurain-project/endurain/pulls/630), [#644](https://codeberg.org/endurain-project/endurain/pulls/644), [#646](https://codeberg.org/endurain-project/endurain/pulls/646) and [#648](https://codeberg.org/endurain-project/endurain/pulls/648)). Conventional Commits are now also enforced via workflow. The contributing guidelines were also updated to reflect these changes.

The Docker images run as root with no reason to keep them that way, and permission handling for the data and logs folders also needed improvement so failures are safer and easier to understand in the future ([#640](https://codeberg.org/endurain-project/endurain/pulls/640)).

The authentication module is also being refactored so that `auth/` becomes the single owner of all authentication concerns ([#625](https://codeberg.org/endurain-project/endurain/issues/625)).

There was also some work done on the Endurain Flutter [app](https://codeberg.org/endurain-project/endurain-flutter), so expect some news in the near future.

## Thank you note

Thank you to everyone who uses, tests, reports issues, translates, sponsors, or contributes to Endurain.

## Newsletter

--8<-- "_snippets/newsletter.html"
