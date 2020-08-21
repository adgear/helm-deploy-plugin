#!/usr/bin/env python
import io, re, argparse, os.path, sys
import oyaml as yaml
from distutils.spawn import find_executable

bash_exe=find_executable('bash')
helm_exe = os.environ.get("HELM_BIN","helm")
debug = os.environ.get("HELM_DEBUG","false")
namespace = os.environ.get("HELM_NAMESPACE","kube-system")
context = os.environ.get("HELM_KUBECONTEXT","")
params = {}

def get_yaml(file):
  with open(file, 'r') as ymlfile:
    return yaml.safe_load(ymlfile)

def run_command(cmd):
  import subprocess
  p = subprocess.Popen(cmd, shell=True, executable=bash_exe,
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  stdout, stderr = p.communicate()
  out = {'out': stdout.decode('utf-8'),'err': stderr.decode('utf-8'),'retcode': p.returncode}
  return out

def walk(node,path=""):
  if debug == "true":
    print(path)

  if not (isinstance(node, list) or isinstance(node, dict)):
    if re.match("\$\(.*\)",str(node)):
      params[path[1:]] = node
    return

  for key, item in node.items():
    if re.match(".*\..*",str(key)):
      key = '"'+key.replace('.','\.')+'"'
    if isinstance(item, list):
      for i, obj in enumerate(item):
        walk(obj, path+"."+key+"["+str(i)+"]")
    else:
      walk(item,path+"."+key)

def generate_sets(args):
  sets={"dry": "","wet": ""}
  cache = {}
  for key, val in params.items():
    vault_args = val[2:-1].split(" ")
    if len(vault_args) == 1:
      vault_args.append("value")
    local_set = 'vault read -field={} {}'.format(vault_args[1],vault_args[0])
    sets["dry"] += '--set {}="$({})" '.format(key,local_set)
    if vault_args[0]+"_"+vault_args[1] in cache:
      secret = {"out": cache[vault_args[0]+"_"+vault_args[1]],"retcode": 0}
    else:
      print("\033[1;33;40mGetting vault secret for {} \033[0m".format(local_set))
      secret = run_command(local_set)
      if secret["retcode"] != 0:
        print("STDOUT:\n {}".format(secret["out"]))
        print("STDERR:\n {}".format(secret["err"]))
        sys.exit(1)
      cache[vault_args[0]+"_"+vault_args[1]] = secret["out"]
    sets["wet"] += '--set {}=\"{}\" '.format(key,secret["out"])
  return sets

def generate_template():
  return "{} {{}} {} -n {} {{}} {} {}".format(
            helm_exe,
            args.name,
            namespace,
            " --kube-context {}".format(context) if context != "" else " ",
            " ".join(other_args))

def process_configs():
  for i in range(len(other_args)):
    if other_args[i] == "-f":
      if os.path.isfile(other_args[i+1]):
        print("Processing {}".format(other_args[i+1]))
        config = get_yaml(other_args[i+1])
        walk(config)
      else:
        print("\033[1;31;40m Value file {} does not exists. Exiting\033[0m".format(other_args[i+1]))
        sys.exit(1)

def install(args,sets):
  print("Running DEPLOY")
  sets["wet"] += "--set partition={}".format(args.canary)
  sets["dry"] += "--set partition={}".format(args.canary)
  template = generate_template()
  return {
            "dry": template.format("upgrade --install", sets["dry"]),
            "wet": template.format("upgrade --install", sets["wet"])
          }

def diff(args,sets):
  print("Running DIFF")
  os.environ["HELM_DEBUG"] = "false"
  print("Debug Off, diff cant be run with, b/o output yaml get corrupted")
  sets["wet"] += "--set partition={}".format(args.canary)
  sets["dry"] += "--set partition={}".format(args.canary)
  template = generate_template()
  return {
            "dry": template.format("diff upgrade", sets["dry"]),
            "wet": template.format("diff upgrade", sets["wet"])
          }

def dispatch(args):
  process_configs()
  sets = generate_sets(args)
  if not args.wet:
    return diff(args,sets)
  else:
    return install(args,sets)

##########################################################################################
parser = argparse.ArgumentParser(prog="helm deploy")
parser.add_argument('--name',     required=True, help='Release name')
parser.add_argument('--canary',   default=0, help='Number of pods to canary')
parser.add_argument('--wet','--yes', dest="wet", action='store_true', help='diff or install')
parser.set_defaults(func=dispatch)
args, other_args = parser.parse_known_args()
if debug == "true":
  print("Args: ", args, other_args)
cmd = args.func(args)
print("Running: "  + cmd["dry"])
data = run_command(cmd["wet"])
print("STDOUT:\n {}".format(data["out"]))
print("STDERR:\n {}".format(data["err"]))
if data["retcode"] != 0:
  sys.exit(1)
sys.exit(0)
