import yaml
import json
import os
import sys
import psycopg2
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


def get_pg_user_password( basedir, pg_user="enterprisedb" ):
  ansible_vault = basedir + "/vault/vault_pass.txt"
  fpath = basedir + "/inventory/group_vars/tag_Cluster_BDR-Gold-Benchmark/secrets/" + pg_user + "_password.yml"
  pg_user_password = Vault(vault_lib=MyVaultLib(ansible_vault=ansible_vault)).load(open(fpath).read())
  return pg_user_password


def export_json(ansible_config):
  with open('inventory.json','w') as j:
    json.dump(ansible_config,j)


def parse_inventory(inventory_dir):
  ansible_config = {}
  for node in os.listdir(inventory_dir):
    f = os.path.join(inventory_dir,node,'01-instance_vars.yml')
    with open(f,'r') as stream:
      o = yaml.safe_load(stream)
      o['hostname'] = node
      ansible_config[node] = o
  if debug_mode is True:
    pprint(ansible_config)
  return ansible_config


def main():

  # Build inventory_dir string
  inventory_dir = None
  basedir = None

  if len(sys.argv) > 1:
    basedir = sys.argv[1]
    inventory_dir = basedir + '/inventory/host_vars'
  else:
    print(f"Usage: {sys.argv[0]} <project_path>")
    exit(1)

  # parse inventory and build ansible_config
  ansible_config = parse_inventory(inventory_dir)

  # get pg superuser password
  pg_user_password = get_pg_user_password( basedir=basedir )

  # For testing, export ansible_config to JSON if desired
  # export_json(ansible_confog)

  # Connect to proxy1
  host = ansible_config['proxy1']['public_ip']
  port = 6432
  dbname = "edb"
  pg_user = "enterprisedb"
  conn = psycopg2.connect(f"host={host} port={port} dbname={dbname} user={pg_user} password={pg_user_password['enterprisedb_password']}")
  cur = conn.cursor()

  # Create table
  cur.execute("CREATE TABLE IF NOT EXISTS test (id serial PRIMARY KEY, num integer, data varchar);")

  # Insert rows
  cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (100, "foobar"))

  # Read row
  cur.execute("SELECT * FROM test;")
  p = cur.fetchone()
  print(f"Should be (100,foobar): {p}")

  # Update row
  cur.execute("UPDATE test SET data=%s WHERE num = %s;", ("newval",100))
  cur.execute("SELECT * FROM test;")
  p = cur.fetchone()
  print(f"Should be (100,newval): {p}")

  # Delete row
  cur.execute("DELETE FROM test;")
  cur.execute("SELECT count(*) FROM test;")
  p = cur.fetchone()
  print(f"should be 0 after delete: {p}")

  # Drop table
  cur.execute("DROP TABLE test;")

  conn.commit()
  cur.close()
  conn.close()


main()
