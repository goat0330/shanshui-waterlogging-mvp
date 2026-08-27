from __future__ import annotations

from datetime import datetime, timezone

from app.cma_source import CmaSourceAdapter


def main() -> int:
    weather_payload = {
        "data": {
            "real": {
                "station": {"code": "58367", "city": "上海"},
                "publish_time": "2026-08-27 11:00",
                "weather": {"temperature": 31.2, "humidity": 73, "rain": 0.0, "info": "多云"},
                "wind": {"direct": "东南风", "power": "3级"},
            },
            "radar": {
                "title": "上海雷达",
                "image": "/radar/example.png",
                "time": "2026-08-27 11:00",
            },
        }
    }
    current = CmaSourceAdapter.parse_nmc_current(weather_payload)
    assert current is not None
    assert current.stationId == "58367"
    assert current.condition == "多云"
    assert current.temperatureC == 31.2

    radar = CmaSourceAdapter.parse_nmc_radar(
        weather_payload,
        fallback_time=datetime.now(timezone.utc),
    )
    assert len(radar) == 1
    assert radar[0].previewUrl.endswith("/radar/example.png")
    assert radar[0].georeferenced is False
    assert radar[0].renderableInCesium is False

    warnings = CmaSourceAdapter.parse_nmc_warnings({
        "data": {"page": {"list": [{
            "alertid": "310000-test",
            "issuetime": "2026/08/27 10:30",
            "title": "上海市气象台发布暴雨黄色预警信号",
        }]}}
    }, province="上海市")
    assert len(warnings) == 1
    assert warnings[0].type == "暴雨"
    assert warnings[0].level == "黄色"
    assert warnings[0].area == "上海市"

    minute = CmaSourceAdapter.decode_json_or_jsonp(
        'qixiao({"msg":"未来两小时有短时降水","times":["11:30","11:31"],"rain":[0.0,0.2,0.4]})'
    )
    frames = CmaSourceAdapter.parse_minute_nowcast(
        minute,
        received_at=datetime(2026, 8, 27, 3, 30, tzinfo=timezone.utc),
    )
    assert [item.offsetMinutes for item in frames] == [0, 30, 60, 120]
    assert frames[0].summary == "未来两小时有短时降水"
    assert all(item.renderableInCesium is False for item in frames)

    custom = CmaSourceAdapter.parse_generic_nowcast({
        "frames": [{
            "offsetMinutes": 30,
            "validAt": "2026-08-27T04:00:00Z",
            "rasterUrl": "https://example.invalid/radar.png",
            "crs": "EPSG:4326",
            "bbox": [120.0, 30.0, 122.0, 32.0],
        }]
    })
    assert custom[0].georeferenced is True
    assert custom[0].renderableInCesium is True

    print("meteorology parser smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
