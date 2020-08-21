## helm-deploy-plugin
This plugin supports only helm3.

### Prerequisites
```bash
helm plugin install https://github.com/databus23/helm-diff
pip install pyyaml oyaml
```

### Install
```bash
helm plugin install https://github.com/adgear/helm-deploy-plugin.git --version master
```

### How to use

1. install plugin
2. set up vault client
3. write your secrets to vault
```bash
vault write secret/mytestsecret value="testsecret"
vault write secret/mytestsecret2 registry="myregistry" password="testpass"
```
4. in value.yaml add
```bash
secret:   "$(secret/mytestsecret)"
registry: "$(secret/mytestsecret2 registry)"
password: "$(secret/mytestsecret2 password)"
```
5. Diff before deploy
```bash
helm deploy --name <RELEASE> -n <NAMESPACE> --kube-context <CONTEXT> -f values.yaml -f global.yaml
```
6. DEPLOY
```bash
helm deploy --name <RELEASE> -n <NAMESPACE> --kube-context <CONTEXT> -f values.yaml --wet
```
8. Remove release
```bash
helm delete <RELEASE>  -n <NAMESPACE> --kube-context <CONTEXT>
```
9. List releases in a namespace
```bash
helm list -n <NAMESPACE> --kube-context <CONTEXT>
```
10. History of release in a namespace
```bash
helm history <RELEASE> -n <NAMESPACE> --kube-context <CONTEXT>
```
11. Help
```bash
# helm deploy --help
usage: helm deploy [-h] --name NAME [--canary CANARY] [--wet]

optional arguments:
  -h, --help       show this help message and exit
  --name NAME      Release name
  --canary CANARY  Used only with statufulsets
  --wet            diff or install
```

### Extra notes
`--canary` could be used to pass number of partitions to statefulsets.
Deploy plugin will add `--set partition=` to helm command.
To use this you have to add this to your manifest file with statefulset:

```yaml
  updateStrategy:
    rollingUpdate:
      partition: {{ default 0 .Values.partition }}
```
