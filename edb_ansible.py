import yaml
import json
import os
import sys
from pprint import pprint
from pathlib import Path
from ansible_vault import Vault, VaultLibABC, make_secrets
from ansible.parsing.vault import VaultLib

debug_mode = False

class MyVaultLib(VaultLibABC):
    def __init__(self, ansible_vault):
        if ansible_vault is None:
          ansible_vault = os.environ.get("ANSIBLE_VAULT_PASSWORD_FILE")
        password = open(ansible_vault).read().strip().encode("utf-8")
        self.vlib = VaultLib(make_secrets(password))

    def encrypt(self, plaintext):
        return self.vlib.encrypt(plaintext)

    def decrypt(self, vaulttext):
        return self.vlib.decrypt(vaulttext)


class EDBAnsible:
  def __init__(self, basedir=None, pg_user="enterprisedb"):
    self.basedir = basedir
    self.pg_user = pg_user
    self.inventory_dir = self.basedir + '/inventory/host_vars'
    self.ansible_vault = self.basedir + '/vault/vault_pass.txt'
    self.debug_mode = False


  def get_pg_user_password(self):
    fpath = self.basedir + "/inventory/group_vars/tag_Cluster_BDR-Gold-Benchmark/secrets/" + self.pg_user + "_password.yml"
    self.pg_user_password = Vault(vault_lib=MyVaultLib(ansible_vault=self.ansible_vault)).load(open(fpath).read())
  

  def export_json(self):
    with open('inventory.json','w') as j:
      json.dump(self.ansible_config,j)
  
  
  def parse_inventory(self):
    ansible_config = {}
    for node in os.listdir(self.inventory_dir):
      f = os.path.join(self.inventory_dir,node,'01-instance_vars.yml')
      with open(f,'r') as stream:
        o = yaml.safe_load(stream)
        o['hostname'] = node
        ansible_config[node] = o
    if self.debug_mode is True:
      pprint(ansible_config)
    self.ansible_config = ansible_config
