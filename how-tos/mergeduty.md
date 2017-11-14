This document is the new version of https://wiki.mozilla.org/ReleaseEngineering/Merge_Duty/Steps. It's heavily inspired by https://gist.github.com/lundjordan/b66bff783b6853e024f6.

# MergeDuty Tasks

**Consists of roughly 4 individual days of work. Each day you must action several sequential tasks. The 4 days are spread out over about 18 days**

## Terminology

* Merge Prep Day: day we prepare for the upcoming 'Release Merge Day' and 'Stabilizing Branch Merge Day'
  * when: day 1 - usually a monday and 1 week before 'Release Merge Day'
* Release Merge Day: day we merge csets from 'm-b -> m-r'
  * when: day 7 usually a mon and 1 week before 'Stabilizing Branch Merge Day'
* Stabilizing Branches Merge Day: day we merge csets from 'm-a -> m-b' and 'm-c -> m-a'
  * when: day 14 usually a mon and 1 day before 'Release Day'
* Release Day: official day of release
  * when: day 15 usually a Tues
* Unthrottle Day: day we unthrottle m-a (usually)
  * when: day 18 usually Fri

## Pre-requirements

1. Edit `~/.hgrc` to include:
```ini
[extensions]
transplant=
mq=
rebase=
graphlog=
```
1. Have your computer wired to a stable Internet connection (several gecko clones and huge pushes are planned).
1. File a merge day bug, if it's not done already. [Example](https://bugzilla.mozilla.org/show_bug.cgi?id=1123369).

## Day 1 - Prep day #1

1.  See the doc <a href="merge-and-staging-instance.md">AWS merge instance</a> to see if using a dedicated instance for merge day is helpful.

2. Make sure you have a fresh copy of [buildbot-configs](https://hg.mozilla.org/build/buildbot-configs/)
```sh
hg clone ssh://hg.mozilla.org/build/buildbot-configs/
```
3. On the merge day bug, create two patches to bump [gecko_versions.json](https://dxr.mozilla.org/build-central/source/buildbot-configs/mozilla/gecko_versions.json). Get them reviewed but **don't land them yet**. Note that reviewboard can't land on buildbot-configs, you will need to push changes manually.
   * patch 1: bump the version for **only mozilla-release**. It will serve Firefox's release candidate. [Example](https://reviewboard.mozilla.org/r/162518/diff/1#index_header).
   * patch 2: bump the remaining branches. This includes mozilla-beta, mozilla-central and comm-beta branches. [Example](https://bug1369535.bmoattachments.org/attachment.cgi?id=8892412).

4. Do a no-op trial run of performing the mozilla-beta -> mozilla-release migration:
```sh
mkdir -p merge_day
cd merge_day
wget https://hg.mozilla.org/build/tools/raw-file/default/buildfarm/utils/archiver_client.py
python archiver_client.py mozharness --destination mozharness-central --repo mozilla-central --rev default --debug  # Central must be used against every branch
python mozharness-central/scripts/merge_day/gecko_migration.py -c merge_day/beta_to_release.py
 ```
5. The script should have created changes, and we can make a diff:
```sh
hg -R build/mozilla-release diff
```

## Day 7 - Release Merge Day

### Reconfigs part 1

1. Look at the merge day bug and see if patches need to land at this stage.
1. Land "patch 1" (the mozilla-release only version bump) to `default` branch, wait for tests to run and confirm they pass in `#releng`
1. The reconfiguration is triggered by a cron job every hour exactly on the hour (`0 * * * *` in crontab). Your options are:
   * Wait for the reconfig to happen via cron.
   * Ask buildduty to manually trigger it.
   * Run it yourself, see [below](#appendix-perform-a-manual-reconfig) for instructions
1. Wait for the go-to-merge email in release-drivers

### Merge beta to release

1. [Close mozilla-beta](https://mozilla-releng.net/treestatus/show/mozilla-beta). Check "Remember this change to undo later". Please enter a good message as the reason for the closure, such as "Mergeduty - closing beta for VERSION RC week"
1. Run the [no-op trial run](#day-1---merge-prep-day) one more time, and show the diff to your co-releaseduty.
1. The diff for `release` should be fairly similar to [this](https://hg.mozilla.org/releases/mozilla-release/rev/70e32e6bf15e), with updated branding as well as the version change.
1. Push your changes:
```sh
python mozharness-central/scripts/merge_day/gecko_migration.py \
  -c selfserve/production.py -c merge_day/beta_to_release.py \
  --create-virtualenv --commit-changes --push
```
:warning: If an issue comes up during this phase, you may not be able to ran this command (or the no-op one) correctly. You may need to publicly backout some tags/changesets to get back in a known state.
1. Upon pushing, `beta` should get a version bump consisting of a `commit` like [this](https://hg.mozilla.org/releases/mozilla-beta/rev/52cefa439a7d) and a `tag` like [this](https://hg.mozilla.org/releases/mozilla-beta/rev/907a3a5c6fed)
1. Verify changesets are visible on [hg pushlog](https://hg.mozilla.org/releases/mozilla-release/pushloghtml) and [Treeherder]( https://treeherder.mozilla.org/#/jobs?repo=mozilla-release). It may take a couple of minutes to appear.

### Bump ESR version

Note: you may have 1 or 2 ESRs to bump.

1. Steps are similar to a merge:
```sh
# go to merge_day directory, created on day 1
ESR_VERSION=52
python mozharness-central/scripts/merge_day/gecko_migration.py -c merge_day/bump_esr.py
hg -R build/mozilla-esr$ESR_VERSION diff
python mozharness-central/scripts/merge_day/gecko_migration.py -c merge_day/bump_esr.py \
  --commit-changes --push
```
1. Verify new changesets popped on https://hg.mozilla.org/releases/mozilla-esr`$ESR_VERSION`/pushloghtml

### Uplift locales

1. There are several tens of repos to upgrade. Using an external machine saves time.  You need access to ffxbld_rsa, so probably use a buildbot master; **Do not copy ffxbld_rsa around!**

```sh
ssh buildbot-master01.bb.releng.use1.mozilla.com
screen
sudo su - cltbld
mkdir l10n && cd l10n
wget https://hg.mozilla.org/build/braindump/raw-file/default/releases-related/beta2release_l10n.sh
chmod 755 beta2release_l10n.sh
export SSH_KEY=/home/cltbld/.ssh/ffxbld_rsa
./beta2release_l10n.sh 2>&1 | tee -a l10n.log  # Can be rerun. Cloned locales are skipped. If a locale failed pushing, delete the repo.
# after you're done, clean up
cd
rm -rf l10n
```

### It's done!

1. Reply to the migration request with the template:

```
This is now complete:
* mozilla-beta is merged to mozilla-release, new version is XX.Y
* l10n mozilla-beta repos are merged to mozilla-release
* esr is now XX.Y.Z
* beta will stay closed until next Monday
```

## Day 11 - Prep day #2
1. Similar to prep day #1 (you may need to redownload `mozharness-central`):
```sh
# go to merge_day directory, created on day 1
python mozharness-central/scripts/merge_day/gecko_migration.py -c merge_day/central_to_beta.py
```

## Day 14 - Stabilizing Branches Merge Day

### Reconfigs part 2

1. Do the same things as part 1, except you should land "patch 2" instead.

### Merge central to beta

It's almost identical to beta to release:

1. Ping l10n folks in `#releng` (usually `Pike`) and send them a heads-up that we're about to perform the merge so that they can coordinate and sync timing of the l10n side of things
1. Make sure you're up-to-date with tip of `central`
```sh
# go to merge_day directory, created on day 1
python mozharness-central/scripts/merge_day/gecko_migration.py -c merge_day/central_to_beta.py
```
1. The script should have created a diff:
```sh
hg -R build/mozilla-beta diff
```
1. Show the diff to your co-releaseduty for review
1. The diff for `beta` should be fairly similar to [this](https://hg.mozilla.org/releases/mozilla-beta/rev/2191d7f87e2e)
1. Push your changes:
```sh
python mozharness-central/scripts/merge_day/gecko_migration.py \
  -c selfserve/production.py -c merge_day/central_to_beta.py \
  --create-virtualenv --commit-changes --push
```
1. Upon pushing, `central` should get a version bump consisting of a `commit` like [this](https://hg.mozilla.org/mozilla-central/rev/52285ea5e54c) and a `tag` like [this](https://hg.mozilla.org/mozilla-central/rev/d6c0df73518b)
1. Verify changesets are visible on [hg pushlog](https://hg.mozilla.org/releases/mozilla-beta/pushloghtml) and [Treeherder]( https://treeherder.mozilla.org/#/jobs?repo=mozilla-beta). It may take a couple of minutes to appear.

### Run the l10n bumper

1. run l10n-bumper against beta
```
ssh buildbot-master01.bb.releng.use1.mozilla.com
sudo su - cltbld
cd /builds/l10n-bumper
python2.7 mozharness/scripts/l10n_bumper.py -c mozharness/configs/l10n_bumper/mozilla-beta.py --ignore-closed-tree
```
1. Ping l10n folks in `#releng` (usually `Pike`) and send them a heads-up that RelEng side of migration is completed

### Trigger new nightlies

1. Trigger nightlies for central. This can be done by:
    1. trigger [nightly-desktop/mozilla-central](https://tools.taskcluster.net/hooks/#project-releng/nightly-desktop%252fmozilla-central) hook
    1. trigger [nightly-fennec/mozilla-central](https://tools.taskcluster.net/hooks/#project-releng/nightly-fennec%252fmozilla-central) hook
1. Tell sheriffs this migration is done either by popping a short message in #sheriffs or ping the `<handle>|sheriffduty` person from #releng.

### Update wikis

1. Updating is done automatically with the proper scripts at hand:
```sh
wget https://hg.mozilla.org/build/tools/raw-file/default/buildfarm/maintenance/wiki_functions.sh
wget https://hg.mozilla.org/build/tools/raw-file/default/buildfarm/maintenance/update_merge_day_wiki.sh
export WIKI_USERNAME=asasaki
export WIKI_PASSWORD=*******
NEW_ESR_VERSION=52  # Only if a new ESR comes up (for instance 52.0esr)
./update_merge_day_wiki.sh # Or ./update_merge_day_wiki.sh -e $NEW_ESR_VERSION
```
1. Check the new values:
  * [NEXT_VERSION](https://wiki.mozilla.org/Template:Version/Gecko/release/next)
  * [CENTRAL_VERSION](https://wiki.mozilla.org/Template:Version/Gecko/central/current)
  * [BETA_VERSION](https://wiki.mozilla.org/Template:Version/Gecko/beta/current)
  * [RELEASE_VERSION](https://wiki.mozilla.org/Template:Version/Gecko/release/current)
  * [Next release date](https://wiki.mozilla.org/index.php?title=Template:NextReleaseDate). This updates
    * [The next ship date](https://wiki.mozilla.org/index.php?title=Template:FIREFOX_SHIP_DATE)
    * [The next merge date](https://wiki.mozilla.org/index.php?title=Template:FIREFOX_MERGE_DATE)
    * [The current cycle](https://wiki.mozilla.org/index.php?title=Template:CURRENT_CYCLE)

### Send merge completion email

Reply to the "please merge m-c => m-b" email. **Please make sure you CC** `thunderbird-drivers@mozilla.org` and `sheriffs@mozilla.org`.  The content should be like:
```
gecko versions are now as follows:
    m-c = 56
    m-b = 55
beta is still closed. Sheriffs may re-open when CI looks good
central nightly builds have been triggered.
Gecko version in bouncer for nightlies will be updated tomorrow
Entries in the wiki have been also updated.
```

### Bump bouncer versions

1. When we have good nightlies from `mozilla-central` with the new version, update the [bouncer](https://bounceradmin.mozilla.com) locations to reflect the new version for following aliases:
    1. [firefox-nightly-latest](https://bounceradmin.mozilla.com/admin/mirror/location/?product__id__exact=2005)
    1. [firefox-nightly-latest-ssl](https://bounceradmin.mozilla.com/admin/mirror/location/?product__id__exact=6508)
    1. [firefox-nightly-latest-l10n](https://bounceradmin.mozilla.com/admin/mirror/location/?product__id__exact=6506)
    1. [firefox-nightly-latest-l10n-ssl](https://bounceradmin.mozilla.com/admin/mirror/location/?product__id__exact=6507)

:note: stub bouncer products no longer require update as they don't specify version in value


:warning: Be careful on how you make changes to bouncer entries. If it is just the version that gets bumped, that's totally fine, but if you also need to change some installer names or anything alike, `space` needs to be encoded to `%20%` and such. See [bug 1386765](https://bugzilla.mozilla.org/show_bug.cgi?id=1386765) for what happened during 57 nightlies migration.

NB: it is expected that the two stub products have a win and win64 location which both point to the same location. We don't have a win64 stub installer, instead the mislabeled 32bit stub selects the correct full installer at runtime.

### Trim bouncer's Check Now list

1. Once per release cycle we should stop checking old releases to see if they're present
1. Visit the [list of check now enabled products](https://bounceradmin.mozilla.com/admin/mirror/product/?all=&checknow__exact=1)
1. you should leave all current and upcoming releases enabled, as well as the updates for watershed releases. Typically this is about 100 products
1. Select all the old releases not covered above, and use the 'Remove Check Now on selected products' option in the Action dropdown


## Appendix: Perform a manual reconfig

A note on reconfigs. If you land any changes to [buildbotcustom](http://hg.mozilla.org/build/buildbotcustom/) or [buildbot-configs](https://hg.mozilla.org/build/buildbot-configs/) repos and want them in production, you'd need a reconfig.
In order to do that, there are a couple of steps needed:

1. Push your changes to `default` branch (can be to either of the two repos if to both if you need to change both)
1. Dump and complete the contents of this file under `~/merge_duty/reconfig.source.sh` with your own credentials
```sh
# Needed if updating wiki - note the wiki does *not* use your LDAP credentials...
export WIKI_USERNAME='Joe Doe'
export WIKI_PASSWORD='********'
```
No need to define Bugzilla integration anymore. Ever since Bugzilla turned on the 2FA, the auth has been troublous so we're not using it anymore for reconfigs. Hence the use of `-b` when calling the script, below.
1. GPG encrypt the file to `reconfig.source.sh.gpg`, so you are the only user to be able to read your credentials.
1. Securely delete the plain text file: `shred --iterations=7 --remove 'reconfig.source.sh'`
1. Run reconfig. This will:
   * clone locally and merge `default` to `production` for [buildbotcustom](http://hg.mozilla.org/build/buildbotcustom/)
   * clone and merge `default` to `production` for [buildbot-configs](https://hg.mozilla.org/build/buildbot-configs/)
   * perform a forced reconfig
   * update wikiwith details about date/time of the reconfig


```sh
now="$(date +'%d-%m-%Y')"
cd ~/merge_duty
# create a temporary directory where all the files and clones are downloaded
# (optional if not having it already)
hg clone http://hg.mozilla.org/build/tools/
cd tools/buildfarm/maintenance/
bash end_to_end_reconfig.sh -b -w <(gpg -d ~/merge_duty/reconfig.source.sh.gpg) -r "$now"   # A folder with the current date will be created
```
:warning: You may be prompted for your gpg key to decrypt the file, but end_to_end_reconfig.sh won't wait. Ensure your password is cached.


## Appendix: What to do if RelMan asks 1 release to be on 2 trains at the same time

Firefox 57 was atypical: Release Management wanted it to be on both mozilla-central and mozilla-beta. The goal was to ship DevEdition 1 week before the planned merge day. This meant Releng had to:
1. Merge m-b => m-r (regular merge per the documentation above)
1. Merge m-c => m-b but leave m-c as is (more details below).
1. Tag m-c to tell the beta cycle started
1. Ask sheriffs to create a relbranch in m-b, so the last Fennec beta (56.0b13) could ship in the meantime.
1. Once RelMan wants to bump Nightly's version number, bump and tag central.

*:information_source: Each command line can be found in the logs of a passed job. Please refer to them. Tags and commit messages are provided in the following examples.*

### Merge m-c => m-b but leave m-c as is.

Some steps in `gecko_migration.py` need to be commented out:
* [Bump version and touch clobber files](https://searchfox.org/mozilla-central/rev/31606bbabc50b08895d843b9f5f3da938ccdfbbf/testing/mozharness/scripts/merge_day/gecko_migration.py#329-339)
* [hg tag the origin repo](https://searchfox.org/mozilla-central/rev/31606bbabc50b08895d843b9f5f3da938ccdfbbf/testing/mozharness/scripts/merge_day/gecko_migration.py#466-469)

Then run `gecko_migration.py` as usual.

### Tag m-c

You have to create a [tag like FIREFOX_BETA_57_BASE](https://hg.mozilla.org/mozilla-central/rev/22ed219fb63a).

# Relbranch in m-b for Fennec

Ask sheriffs to create [a relbranch like this one](https://hg.mozilla.org/releases/mozilla-beta/shortlog/FIREFOX_56b13_RELBRANCH). RelMan can specify the relbranch on ship-it and builds starts automatically. However, we had to verify locales we still using the right beta repos ([Bug 1397721](https://bugzil.la/1397721)).
Moreover, the bump task in release promotion will fail. You have to [bump it manually](https://hg.mozilla.org/releases/mozilla-beta/rev/418902381c4b) and [tag it manually](https://hg.mozilla.org/releases/mozilla-beta/rev/ef07d617a488) too.

# Bump and tag central

A new tag is needed to specify the end of the nightly cycle, for instance: [FIREFOX_NIGHTLY_57_END](https://hg.mozilla.org/mozilla-central/rev/1ca411f5e97b). Then you have to clobber and bump versions in m-c, just [like the following](https://hg.mozilla.org/mozilla-central/rev/835a92b19e3d).
