import sys
import psycopg2
from edb_ansible import EDBAnsible

def main():

  # Build EDBAnsible object
  edbcluster = None

  if len(sys.argv) > 1:
    edbcluster = EDBAnsible(basedir=sys.argv[1])
  else:
    print(f"Usage: {sys.argv[0]} <project_path>")
    exit(1)

  # parse inventory and build ansible_config
  edbcluster.parse_inventory()

  # get pg superuser password
  edbcluster.get_pg_user_password()

  # For testing, export ansible config to JSON if desired
  # edbcluster.export_json()

  # Connect to proxy1
  host = edbcluster.ansible_config['proxy1']['public_ip']
  port = 6432
  dbname = "edb"
  pg_user = "enterprisedb"
  conn = psycopg2.connect(f"host={host} port={port} dbname={dbname} user={pg_user} password={edbcluster.pg_user_password['enterprisedb_password']}")
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
