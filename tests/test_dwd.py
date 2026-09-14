import io
import zipfile

import httpx

from berlin_exposure_twin.providers.dwd import DWDClient, parse_semicolon_product, parse_station_metadata


def test_dwd_missing_sentinel_is_dropped() -> None:
    text = "STATIONS_ID;MESS_DATUM;QN_9;TT_TU;RF_TU;eor\n00433;2026010112;3;-999;81;eor\n"
    assert parse_semicolon_product(text, variable="air_temperature") == []


def test_dwd_temperature_has_explicit_unit_and_utc() -> None:
    text = "STATIONS_ID;MESS_DATUM;QN_9;TT_TU;RF_TU;eor\n00433;2026010112;3;4.2;81;eor\n"
    result = parse_semicolon_product(text, variable="air_temperature")
    assert result[0].unit == "°C"
    assert result[0].timestamp.isoformat() == "2026-01-01T12:00:00+00:00"


def test_dwd_station_metadata_parser() -> None:
    text = (
        "Stations_id von_datum bis_datum Stationshoehe geoBreite geoLaenge Stationsname Bundesland\n"
        "-----\n"
        "00433 19480101 20261231 48 52.4675 13.4021 Berlin-Tempelhof  Berlin\n"
    )
    rows = parse_station_metadata(text)
    assert rows[0]["station_id"] == "00433"
    assert rows[0]["name"] == "Berlin-Tempelhof"


def test_dwd_client_fetches_recent_product_from_mocked_archive() -> None:
    station_text = (
        "Stations_id von_datum bis_datum Stationshoehe geoBreite geoLaenge Stationsname Bundesland\n"
        "-----\n"
        "00433 19480101 20261231 48 52.4675 13.4021 Berlin-Tempelhof  Berlin\n"
    )
    product_text = "STATIONS_ID;MESS_DATUM;QN_9;TT_TU;RF_TU;eor\n00433;2026010112;3;4.2;81;eor\n"
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("produkt_tu_stunde_00433.txt", product_text)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("TU_Stundenwerte_Beschreibung_Stationen.txt"):
            return httpx.Response(200, text=station_text)
        if request.url.path.endswith("stundenwerte_TU_00433_akt.zip"):
            return httpx.Response(200, content=payload.getvalue())
        return httpx.Response(404)

    client = DWDClient(transport=httpx.MockTransport(handler))
    stations = client.stations("air_temperature")
    observations = client.recent_observations("00433", "air_temperature")
    client.close()
    assert stations[0]["name"] == "Berlin-Tempelhof"
    assert observations[0].value == 4.2


def test_dwd_station_metadata_accepts_whitespace_separated_current_layout() -> None:
    text = (
        "Stations_id von_datum bis_datum Stationshoehe geoBreite geoLaenge Stationsname Bundesland\n"
        "-----\n"
        "00433 19510101 20261231 48 52.4675 13.4021 Berlin Tempelhof Berlin\n"
    )
    rows = parse_station_metadata(text)
    assert rows[0]["station_id"] == "00433"
    assert rows[0]["name"] == "Berlin Tempelhof"
    assert rows[0]["state"] == "Berlin"


def test_dwd_wind_uses_current_synop_dataset() -> None:
    dataset, product_code, metadata_name = DWDClient._dataset("wind_speed")
    assert dataset == "wind_synop"
    assert product_code == "F"
    assert metadata_name == "F_Stundenwerte_Beschreibung_Stationen.txt"


def test_dwd_discovers_only_station_ids_with_recent_archives() -> None:
    directory_html = """
    <a href="stundenwerte_TU_00433_akt.zip">stundenwerte_TU_00433_akt.zip</a>
    <a href="stundenwerte_TU_00582_akt.zip">stundenwerte_TU_00582_akt.zip</a>
    <a href="TU_Stundenwerte_Beschreibung_Stationen.txt">metadata</a>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/air_temperature/recent/"):
            return httpx.Response(200, text=directory_html)
        return httpx.Response(404)

    client = DWDClient(transport=httpx.MockTransport(handler))
    station_ids = client.available_recent_station_ids("air_temperature")
    client.close()

    assert station_ids == {"00433", "00582"}
