import argparse,json,sys
from pathlib import Path
from bridge import core
def main():
 parser=argparse.ArgumentParser(description='CK3 Character Toolkit：独立 character 适配器与运行时前置构建器')
 sub=parser.add_subparsers(dest='command',required=True)
 p=sub.add_parser('check');p.add_argument('path')
 p=sub.add_parser('inspect');p.add_argument('source');sub.add_parser('runtime-zip');sub.add_parser('doctor');sub.add_parser('profiles');sub.add_parser('public-zip');sub.add_parser('serve')
 for action in ('audit','build'):
  p=sub.add_parser(action);p.add_argument('profile')
 p=sub.add_parser('batch');p.add_argument('profiles',nargs='+')
 p=sub.add_parser('compile');p.add_argument('bundle_id');p.add_argument('packages',nargs='+')
 p=sub.add_parser('install');p.add_argument('bundle');p.add_argument('--mod-root',required=True);p.add_argument('--storage-root')
 p=sub.add_parser('verify-install');p.add_argument('transaction')
 p=sub.add_parser('trace-state');p.add_argument('path');p.add_argument('state')
 p=sub.add_parser('rollback');p.add_argument('transaction')
 args=parser.parse_args()
 if args.command=='doctor':result=core.doctor()
 elif args.command=='check':
  from bridge.audit_commands import inspect_package
  out,report=inspect_package(args.path);print(json.dumps({'report_directory':str(out),'passed':report['passed'],'issues':report['issues']},ensure_ascii=False,indent=2));return 0 if report['passed'] else 2
 elif args.command=='inspect':
  from bridge.intake import inspect_source
  result=str(inspect_source(args.source))
 elif args.command=='profiles':result=[core.profile(p.stem) for p in (core.ROOT/'profiles.local').glob('*.json')]
 elif args.command in ('audit','build'):result=str(core.run(args.profile,args.command))
 elif args.command=='batch':
  result=core.build_batch(args.profiles);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if all(x['ok'] for x in result) else 1
 elif args.command=='compile':result=str(core.compile_bundle(args.packages,args.bundle_id))
 elif args.command=='install':result=str(core.install_bundle(args.bundle,args.mod_root,args.storage_root or core.settings().get('storage_root')))
 elif args.command=='verify-install':
  from bridge.installation import verify
  result=verify(args.transaction);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['installed_files_verified'] else 2
 elif args.command=='trace-state':
  from bridge.action_trace import trace
  result=trace(args.path,args.state)
 elif args.command=='rollback':core.rollback(args.transaction);result='已回退'
 elif args.command=='runtime-zip':
  from bridge.release import runtime_zip
  result=str(runtime_zip())
 elif args.command=='public-zip':result=str(core.public_zip())
 elif args.command=='serve':
  from bridge.webapp import serve
  serve();return 0
 print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as exc:print('ERROR:',str(exc),file=sys.stderr);sys.exit(1)
