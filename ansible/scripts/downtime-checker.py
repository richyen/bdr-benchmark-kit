# -*- coding: utf-8 -*-

import argparse
import psycopg2
import time
from datetime import datetime as dt
from subprocess import Popen, PIPE

def connect(conn_string):
    while True:
        try:
            print("%s INFO: Connecting to PostgreSQL..." % dt.now())
            conn = psycopg2.connect(conn_string)
            print("%s INFO: Connected." % dt.now())
            return conn
        except psycopg2.Error as e:
            print("%s ERROR: Cannot connect, new try." % dt.now())


def monitor_downtime(conn, pg):
    bdr_leader_init = None
    bdr_leader_current = None
    downtime = None

    while True:
        try:
            cur = conn.cursor()
            # Not leader found yet? then this is the first iteration and we
            # must remove any data from the ping table.
            if bdr_leader_init is None:
                cur.execute("TRUNCATE ping")

            # Get BDR leader name
            if bdr_leader_init is None or bdr_leader_current is None:
                cur.execute("SELECT node_name FROM bdr.local_node_info()")
                r = cur.fetchone()
                if bdr_leader_init is None:
                    bdr_leader_init = r[0]
                if bdr_leader_current is None:
                    bdr_leader_current = r[0]

            # Insert a new record into the ping table
            cur.execute(
                "INSERT INTO ping (bdr_node) VALUES "
                "((SELECT node_name FROM bdr.local_node_info()))"
            )
            conn.commit()

            # If the current BDR leader node is different from the initial one,
            # then this must indicate a new BDR leader node has been promoted.
            if bdr_leader_current != bdr_leader_init:
                cur2 = conn.cursor()
                cur2.execute(
                    "SELECT MIN(timestamp) - ("
                    "  SELECT MAX(timestamp) FROM ping where bdr_node = %s"
                    ") FROM ping WHERE bdr_node = %s",
                    (bdr_leader_init, bdr_leader_current)
                )
                r2 = cur2.fetchone()
                downtime = r2[0]
                conn.commit()
                return downtime

        except psycopg2.OperationalError as e:
            # Connection to the database has been lost, this must be due to a
            # leader change, then we reset bdr_leader_current to None.
            bdr_leader_current = None
            print("%s ERROR: Connection lost" % dt.now())
            conn = connect(pg)
        except psycopg2.DatabaseError as e:
            bdr_leader_current = None
            print(e)
            print("%s ERROR: Cannot insert message" % dt.now())
            conn = connect(pg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--pg',
        dest='pg',
        type=str,
        help="Postgres connection string to the Harp proxy node.",
        default='',
    )
    parser.add_argument(
        '--proxy', '-P',
        dest='proxy',
        type=str,
        help="Additional traffic: Harp proxy address.",
    )
    parser.add_argument(
        '--dbname', '-D',
        dest='dbname',
        default="edb",
        type=str,
        help="Additional traffic: Database name. Default: %(default)s",
    )
    parser.add_argument(
        '--port', '-p',
        dest='port',
        type=int,
        help="Additional traffic: Harp proxy port. Default: %(default)s",
        default=6432,
    )
    parser.add_argument(
        '--warehouse', '-w',
        dest='warehouse',
        type=int,
        help="Additional traffic: number of TPC-C warehouse. Default: %(default)s",
        default=5000,
    )
    parser.add_argument(
        '--terminal', '-t',
        dest='terminal',
        type=int,
        help="Additional traffic: number of TPC-C terminals. Default: %(default)s",
        default=12,
    )
    env = parser.parse_args()

    conn = connect(env.pg)
    downtime = monitor_downtime(conn, env.pg)
    print("Downtime: %s" % downtime)
    conn.close()


if __name__ == '__main__':
    main()
