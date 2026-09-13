"""
百度地图 Web 服务工具层
封装 Place / Geocoding / Direction Lite / Weather API，
对外保持与原 AmapTools 相同的方法签名和返回结构，方便 Agent 复用。

内部统一用 "经度,纬度"（lng,lat）字符串，调用百度接口时再转成其要求的 lat,lng。
"""

import time
from typing import Optional

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _split_lnglat(location: str):
    if not location or "," not in location:
        return None
    a, b = location.split(",", 1)
    try:
        x, y = float(a.strip()), float(b.strip())
    except ValueError:
        return None
    # 若第一个数像纬度，则输入已是 lat,lng
    if 3 <= x <= 54 and 73 <= y <= 135:
        return y, x
    return x, y


def _to_baidu_latlng(location: str) -> str:
    pair = _split_lnglat(location)
    if not pair:
        return location
    lng, lat = pair
    return f"{lat},{lng}"


def _loc_str(lng: float, lat: float) -> str:
    return f"{lng},{lat}"


def _parse_path(path: str):
    """百度 path → [[lng, lat], ...]"""
    pts = []
    if not path:
        return pts
    for pair in path.replace("|", ";").split(";"):
        if "," not in pair:
            continue
        a, b = pair.split(",", 1)
        try:
            x, y = float(a), float(b)
        except ValueError:
            continue
        if 3 <= x <= 54 and 73 <= abs(y) <= 135:
            pts.append([y, x])
        else:
            pts.append([x, y])
    return pts


class BaiduTools:
    """百度地图 REST API 工具集"""

    def __init__(self, api_key: str, base_url: str = "https://api.map.baidu.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "TravelAgent/1.0"})
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get(self, path: str, params: dict) -> dict:
        params = dict(params)
        params["ak"] = self.api_key
        params.setdefault("output", "json")
        max_retries = 3
        retry_delay = 1
        for attempt in range(max_retries):
            try:
                resp = self.session.get(
                    f"{self.base_url}{path}",
                    params=params,
                    timeout=(5, 15),
                    verify=True,
                )
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status")
                if status not in (0, "0"):
                    return {
                        "error": data.get("message") or data.get("msg") or "百度API返回错误",
                        "status": status,
                    }
                return data
            except requests.exceptions.SSLError as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                return {"error": f"SSL连接失败 (已重试{max_retries}次): {e}"}
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                return {"error": f"请求超时 (已重试{max_retries}次): {e}"}
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                return {"error": f"连接失败 (已重试{max_retries}次): {e}"}
            except requests.RequestException as e:
                return {"error": f"请求百度API失败: {e}"}
        return {"error": "请求失败: 未知错误"}

    def _poi_item(self, p: dict, include_distance: bool = False) -> dict:
        loc = p.get("location") or {}
        lng = loc.get("lng")
        lat = loc.get("lat")
        detail = p.get("detail_info") or {}
        item = {
            "name": p.get("name"),
            "address": p.get("address") or detail.get("tag") or "",
            "type": p.get("detail") or detail.get("classified_poi_tag") or detail.get("tag") or "",
            "location": _loc_str(lng, lat) if lng is not None and lat is not None else "",
            "tel": p.get("telephone") or "",
            "rating": str(detail.get("overall_rating") or ""),
            "cost": str(detail.get("price") or ""),
            "opening_time": detail.get("shop_hours") or "",
            "photo_url": detail.get("image") or "",
        }
        if include_distance:
            item["distance"] = str(p.get("detail_info", {}).get("distance") or p.get("distance") or "")
        return item

    def search_pois(self, keywords: str, city: str, types: str = "",
                    page_size: int = 10, page: int = 1) -> dict:
        query = keywords or types or "景点"
        params = {
            "query": query,
            "region": city,
            "city_limit": "true",
            "page_size": min(int(page_size or 10), 20),
            "page_num": max(int(page or 1) - 1, 0),
            "scope": 2,
        }
        raw = self._get("/place/v2/search", params)
        if "error" in raw:
            return raw
        pois = [self._poi_item(p) for p in raw.get("results") or []]
        return {"count": len(pois), "pois": pois}

    def search_around(self, location: str, keywords: str = "", types: str = "",
                      radius: int = 3000, page_size: int = 10) -> dict:
        params = {
            "query": keywords or types or "生活服务",
            "location": _to_baidu_latlng(location),
            "radius": radius,
            "page_size": min(int(page_size or 10), 20),
            "page_num": 0,
            "scope": 2,
        }
        raw = self._get("/place/v2/search", params)
        if "error" in raw:
            return raw
        pois = [self._poi_item(p, include_distance=True) for p in raw.get("results") or []]
        return {"count": len(pois), "pois": pois}

    def geocode(self, address: str, city: str = "") -> dict:
        params = {"address": address}
        if city:
            params["city"] = city
        raw = self._get("/geocoding/v3/", params)
        if "error" in raw:
            return raw
        result = raw.get("result") or {}
        loc = result.get("location") or {}
        lng, lat = loc.get("lng"), loc.get("lat")
        if lng is None or lat is None:
            return {"count": 0, "geocodes": []}
        addr = result.get("formatted_address") or address
        geocode = {
            "formatted_address": addr,
            "location": _loc_str(lng, lat),
            "province": (result.get("addressComponent") or {}).get("province", ""),
            "city": (result.get("addressComponent") or {}).get("city", "") or city,
            "district": (result.get("addressComponent") or {}).get("district", ""),
        }
        return {"count": 1, "geocodes": [geocode]}

    def regeocode(self, location: str) -> dict:
        params = {"location": _to_baidu_latlng(location), "coordtype": "bd09ll"}
        raw = self._get("/reverse_geocoding/v3/", params)
        if "error" in raw:
            return raw
        result = raw.get("result") or {}
        ac = result.get("addressComponent") or {}
        return {
            "formatted_address": result.get("formatted_address"),
            "province": ac.get("province"),
            "city": ac.get("city"),
            "district": ac.get("district"),
        }

    def _route_summary(self, origin: str, destination: str, mode: str, extra: Optional[dict] = None) -> dict:
        params = {
            "origin": _to_baidu_latlng(origin),
            "destination": _to_baidu_latlng(destination),
        }
        if extra:
            params.update(extra)
        path = {
            "driving": "/directionlite/v1/driving",
            "walking": "/directionlite/v1/walking",
            "bicycling": "/directionlite/v1/riding",
            "riding": "/directionlite/v1/riding",
            "transit": "/directionlite/v1/transit",
        }.get(mode, "/directionlite/v1/driving")
        raw = self._get(path, params)
        if "error" in raw:
            return raw
        return raw

    def route_driving(self, origin: str, destination: str, strategy: int = 0) -> dict:
        raw = self._route_summary(origin, destination, "driving")
        if "error" in raw:
            return raw
        routes = []
        for path in (raw.get("result") or {}).get("routes") or []:
            routes.append({
                "distance": path.get("distance"),
                "duration": path.get("duration"),
                "strategy": strategy,
                "toll_distance": path.get("toll"),
                "tolls": path.get("toll"),
            })
        return {"count": len(routes), "routes": routes}

    def route_transit(self, origin: str, destination: str, city: str, strategy: int = 0) -> dict:
        raw = self._route_summary(origin, destination, "transit", {"region": city})
        if "error" in raw:
            return raw
        result = raw.get("result") or {}
        transits = []
        for t in (result.get("routes") or [])[:3]:
            transits.append({
                "cost": t.get("price") or t.get("cost"),
                "duration": t.get("duration"),
                "walking_distance": t.get("walking_distance"),
                "nightflag": 0,
            })
        return {
            "distance": (result.get("routes") or [{}])[0].get("distance") if transits else 0,
            "count": len(transits),
            "transits": transits,
        }

    def route_walking(self, origin: str, destination: str) -> dict:
        raw = self._route_summary(origin, destination, "walking")
        if "error" in raw:
            return raw
        routes = []
        for path in (raw.get("result") or {}).get("routes") or []:
            routes.append({
                "distance": path.get("distance"),
                "duration": path.get("duration"),
            })
        return {"count": len(routes), "routes": routes}

    def route_with_polyline(self, o_lng, o_lat, d_lng, d_lat, mode="driving", city=""):
        origin = _loc_str(o_lng, o_lat)
        destination = _loc_str(d_lng, d_lat)
        extra = {"region": city} if city and mode == "transit" else None
        raw = self._route_summary(origin, destination, mode, extra)
        result = {"distance": 0, "duration": 0, "polyline": []}
        if "error" in raw:
            result["polyline"] = [[o_lng, o_lat], [d_lng, d_lat]]
            result["error"] = raw.get("error")
            return result

        routes = (raw.get("result") or {}).get("routes") or []
        if not routes:
            result["polyline"] = [[o_lng, o_lat], [d_lng, d_lat]]
            return result

        route = routes[0]
        poly = []
        for step in route.get("steps") or []:
            poly.extend(_parse_path(step.get("path") or ""))
            for inner in step.get("steps") or []:
                poly.extend(_parse_path(inner.get("path") or ""))
        if not poly:
            poly = [[o_lng, o_lat], [d_lng, d_lat]]
        result = {
            "distance": int(route.get("distance") or 0),
            "duration": int(route.get("duration") or 0),
            "polyline": poly,
        }
        if route.get("taxi_fee") is not None:
            result["taxi_cost"] = route.get("taxi_fee")
        if route.get("price") is not None:
            result["cost"] = route.get("price")
        return result

    def query_weather(self, city: str, extensions: str = "base") -> dict:
        geo = self.geocode(address=city, city=city)
        if "error" in geo or not geo.get("geocodes"):
            return {"error": geo.get("error", "无法定位城市")}
        loc = _split_lnglat(geo["geocodes"][0]["location"])
        if not loc:
            return {"error": "无法定位城市"}
        lng, lat = loc
        raw = self._get("/weather/v1/", {
            "location": f"{lng},{lat}",
            "data_type": "all" if extensions == "all" else "now",
        })
        if "error" in raw:
            return raw
        weather = (raw.get("result") or {})
        now = weather.get("now") or {}
        forecasts = weather.get("forecasts") or []
        if extensions == "all" and forecasts:
            return {
                "city": weather.get("location", {}).get("name") or city,
                "casts": [
                    {
                        "date": c.get("date"),
                        "week": c.get("week"),
                        "dayweather": c.get("text_day"),
                        "nightweather": c.get("text_night"),
                        "daytemp": str(c.get("high", "")),
                        "nighttemp": str(c.get("low", "")),
                    }
                    for c in forecasts
                ],
            }
        if now:
            return {
                "city": weather.get("location", {}).get("name") or city,
                "weather": now.get("text"),
                "temperature": str(now.get("temp", "")),
                "winddirection": now.get("wind_dir"),
                "windpower": now.get("wind_class"),
                "humidity": str(now.get("rh", "")),
                "reporttime": now.get("uptime") or now.get("obs_time") or "",
            }
        return {"error": "无天气数据"}

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        method = getattr(self, tool_name, None)
        if method is None:
            return {"error": f"未知工具: {tool_name}"}
        try:
            return method(**arguments)
        except TypeError as e:
            return {"error": f"工具参数错误: {e}"}
