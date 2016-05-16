import sys
import argparse
import datetime

from releasewarrior.commands import CreateRelease, UpdateRelease, Postmortem, Outstanding
from releasewarrior.commands import BumpBuildnum, SyncRelease


def parse_args():
    parser = argparse.ArgumentParser(
        description="ReleaseWarrior: helping you keep track of releases in flight"
    )
    subparser = parser.add_subparsers(title='valid sub-commands',
                                      description="run `release <command> --help` for usage details")

    # sub-commands
    parser_create = subparser.add_parser(
        'create', help="start tracking a new release currently in flight"
    )
    parser_create.set_defaults(command=CreateRelease())

    parser_update = subparser.add_parser(
        'update', help="update state of an existing release"
    )
    parser_update.set_defaults(command=UpdateRelease())

    parser_bump_buildnum = subparser.add_parser(
        'bump_buildnum', help="abort tracking and bump current buildnum of a release"
    )
    parser_bump_buildnum.set_defaults(command=BumpBuildnum())

    parser_postmortem = subparser.add_parser(
        'postmortem', help="archive completed releases and create postmortem based their issues"
    )
    parser_postmortem.set_defaults(command=Postmortem())

    parser_outstanding = subparser.add_parser(
        'outstanding', help="output current, incomplete tasks from all open releases"
    )
    parser_outstanding.set_defaults(command=Outstanding())

    parser_sync = subparser.add_parser(
        'sync', help="re-generates wiki of a given release based on current data file"
    )
    parser_sync.set_defaults(command=SyncRelease())

    for subcommand in [parser_create, parser_update, parser_bump_buildnum, parser_sync]:

        # each of these sub-commands take the following 2 positional args first
        subcommand.add_argument('version', help='version of release in question. '
                                                'valid examples:\n'
                                                '   for betas: 47.0b1'
                                                '   for releases: 46.0  or 46.0.1'
                                                '   for esr: 45.0esr or 45.0.1esr')
        subcommand.add_argument('product', choices=['firefox', 'fennec', 'thunderbird'],
                                help='product of release in question')


    # update options
    parser_update.add_argument('--graphid', '--taskcluster_graphid', dest='graphid',
                               help='taskcluster graphid used for release in question')
    parser_update.add_argument('--shipit', '--submitted-shipit', action='store_true',
                               help='update release that we submitted to ship it (started release)')
    parser_update.add_argument('--cdntest', '--emailed-cdntest', action='store_true',
                               help='update release that we emailed drivers that release is on cdntest')
    parser_update.add_argument('--balrog', '--submitted-balrog', action='store_true',
                               help='update release that we have submitted to balrog')
    parser_update.add_argument('--post', '--post-released', action='store_true',
                               help='update release that we have ran post release task')
    parser_update.add_argument('--issue', '--issue', action='append', dest='issues',
                               help='issue to add to release in question')

    # postmortem options
    parser_postmortem.add_argument('date', type=lambda x: datetime.datetime.strptime(x, "%Y-%m-%d"),
                                   help='the date of the postmortem meeting')

    return parser.parse_args()

def main():

    if sys.version_info.major != 3:
        print("y u no py 3 yo?")
        sys.exit()

    args = parse_args()
    args.command.run(args)  # <3 argparse for this



