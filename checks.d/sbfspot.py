from datadog_checks.base import AgentCheck
import sqlite3

# Le contenu de la variable spéciale __version__ sera indiqué dans la page de statut de l'Agent
__version__ = "1.0.0"


class SBFSpotCheck(AgentCheck):
    """
    This is a check for SBFspot (https://github.com/SBFspot/SBFspot/wiki).

    It supports only the sqlite3 backend but should be easy to adapt to
    other databases.

    To make sure you don't have permission issues run:
    $ sqlite3 /var/lib/smadata/SBFspot.db 'PRAGMA journal_mode=delete;'

    See https://github.com/SBFspot/SBFspot/blob/master/SBFspot/CreateSQLiteDB.sql#L11 for the schema

    TODO:
    - Make the DB configurable
    - Make the list of polled inverters configurable
    - Export more metrics?
    """

    DB_URI = "file:/var/lib/smadata/SBFspot.db?mode=ro&cache=private"

    def __init__(self, *args, **kwargs):
        super(SBFSpotCheck, self).__init__(*args, **kwargs)

    def check_inverters(self, db):
        db.row_factory = sqlite3.Row
        res = db.execute('SELECT * FROM "main"."Inverters";')
        for inverter in res:
            self.check_inverter(db, inverter)

    def check_inverter(self, db, inverter):
        tags = [
            "inverter_sn:" + str(inverter["Serial"]).strip(),
            "inverter_name:" + inverter["Name"].strip(),
            "inverter_type:" + inverter["Type"].strip(),
            "inverter_sw_version:" + inverter["SW_Version"].strip(),
            "inverter_status:" + inverter["Status"].strip().lower(),
            "inverter_grid_relay:" + inverter["GridRelay"].strip().lower(),
        ]
        prefix = "sbfspot."

        cur = db.execute(
            'SELECT * FROM "main"."vwSpotData" WHERE Serial = ? LIMIT 1;',
            (inverter["Serial"],),
        )
        data = cur.fetchone()
        if not data:
            return

        for f in [
            "Pdc1",
            "Pdc2",
            "Idc1",
            "Idc2",
            "Udc1",
            "Udc2",
            "Pac1",
            "Pac2",
            "Pac3",
            "Iac1",
            "Iac2",
            "Iac3",
            "Uac1",
            "Uac2",
            "Uac3",
            "PdcTot",
            "PacTot",
        ]:
            self.gauge(prefix + f.lower(), data[f], tags=tags)

        running = data["BT_Signal"] > 0

        self.gauge(prefix + "running", running, tags=tags)
        self.gauge(prefix + "bt_signal", data["BT_Signal"], tags=tags)

        if not running:
            return

        self.gauge(prefix + "timestamp", inverter["TimeStamp"], tags=tags)

        self.gauge(prefix + "total_pac", inverter["TotalPac"], tags=tags)
        self.monotonic_count(prefix + "pac", inverter["TotalPac"], tags=tags)

        self.gauge(prefix + "energy_today", inverter["EToday"], tags=tags)
        self.gauge(prefix + "energy_total", inverter["ETotal"], tags=tags)
        self.monotonic_count(prefix + "energy", inverter["ETotal"], tags=tags)

        self.gauge(prefix + "operating_time", inverter["OperatingTime"], tags=tags)
        self.gauge(prefix + "feed_in_time", inverter["FeedInTime"], tags=tags)
        self.gauge(prefix + "temperature", inverter["Temperature"], tags=tags)

        self.gauge(prefix + "efficiency", data["Efficiency"], tags=tags)

    def check(self, instance):
        try:
            db = sqlite3.connect(self.DB_URI, uri=True)
            self.check_inverters(db)
        finally:
            db.close()
