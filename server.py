from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import sqlite3
import os
import json
import urllib.parse
import time

# ---- Level 1: Home & About -----
from Level1_query import get_home_stats, get_students, get_personas, get_fun_facts

# ---- Level 2: People & Injury + Accident Condition ----
from Level2_query import injury_summary, injury_summary_by_sex, pictogram_data, ejected_hospital_table, \
    get_age_groups, get_injury_levels, get_road_user_types, get_light_conditions

# ---- Level 3: People Analysis + Accident Analysis ----
from Level3_query import people_analysis, people_analysis_chart, get_accident_analysis

MIME = {
    ".css" : "text/css", ".js" : "application/javascript",
    ".png" : "image/png", ".jpg" : "image/jpeg",
    ".ico" : "image/x-icon", ".svg" : "image/svg+xml",
}

print("LOADING SERVER CODE")

def render_page(page_title, content_html):
    with open("templates/base.html", "r", encoding="utf-8") as f:
        base = f.read()
    with open("templates/navbar.html", "r", encoding="utf-8") as f:
        navbar = f.read()
    with open("templates/footer.html", "r", encoding="utf-8") as f:
        footer = f.read()

    base = base.replace("{{NAVBAR}}", navbar)
    base = base.replace("{{PAGE_TITLE}}", page_title)
    base = base.replace("{{PAGE_CONTENT}}", content_html)
    base = base.replace("{{FOOTER}}", footer)
    return base

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        params = urllib.parse.parse_qs(parsed_path.query)

        if path == "/":
            self.handle_simple_page("Home", "templates/home.html")
        elif path == "/about":
            self.handle_simple_page("About", "templates/about.html")
        elif path == "/accident_condition":
            self.handle_simple_page("Accident Condition", "templates/accident_condition.html")
        elif path == "/people_and_injury":
            self.handle_simple_page("People and Injury", "templates/people_and_injury.html")
        elif path == "/accident_analysis":
            self.handle_simple_page("Accident Analysis", "templates/accident_analysis.html")
        elif path == "/people_analysis":
            self.handle_simple_page("People Analysis", "templates/people_analysis.html")

        elif path.startswith("/static/"):
            self.handle_static(path)

        # --- API Level 1 ---
        elif path == "/api/home":
            self.send_json(get_home_stats())

        elif path == "/api/fun-facts":
            self.send_json(get_fun_facts())

        elif path == "/api/about":
            try:
                self.send_json({
                    "students": get_students(),
                    "personas": get_personas(),
                })
            except Exception as e:
                print(f"Error in /api/about: {e}")
                self.send_json({"error": str(e)})

        # --- API Level 2 ---
        elif path == "/api/injury-summary":
            levels = [int(x) for x in params.get("level", [])]
            self.send_json(injury_summary(levels or None))

        elif path == "/api/injury-summary-by-sex":
            levels = [int(x) for x in params.get("level", [])]
            self.send_json(injury_summary_by_sex(levels or None))

        elif path == "/api/pictogram":
            ages   = params.get("age", None)
            levels = [int(x) for x in params.get("level", [])]
            self.send_json(pictogram_data(ages, levels or None))

        elif path == "/api/ejected-table":
            filters = {
                "ejected":      params.get("ejected", []),
                "hospital":     params.get("hospital", []),
                "age_groups":   params.get("age", []),
                "person_types": params.get("type", []),
            }
            filters = {k: v for k, v in filters.items() if v}
            self.send_json(ejected_hospital_table(filters))

        elif path == "/api/filter-options":
            self.send_json({
                "age_groups":       get_age_groups(),
                "injury_levels":    get_injury_levels(),
                "person_types":     get_road_user_types(),
                "light_conditions": get_light_conditions(),
            })

        elif path == "/api/accident-conditions":
            condition = params.get("condition", ["road"])[0]
            postcode  = params.get("postcode",  [None])[0]
            from Level2_query import get_accident_conditions
            result = get_accident_conditions(condition, postcode)
            if result is None:
                self.send_error(400, "Invalid condition")
            else:
                self.send_json(result)

        # --- API Level 3 ---
        elif path == "/api/people-analysis":
            filters = {k: v for k, v in {
                "level": params.get("level", []),
                "age":   params.get("age", []),
                "light": params.get("light", []),
            }.items() if v}
            table = people_analysis(filters)

            chart_data = {}
            for r in table:
                age = r["age"]
                if age not in chart_data:
                    chart_data[age] = []
                chart_data[age].append(r["injury_rate"])
            chart = [{"age": age, "injury_rate": round(sum(rates)/len(rates), 2)}
                    for age, rates in chart_data.items()]

            self.send_json({"table": table, "chart": chart})

        elif path == "/api/accident-analysis":
            try:
                postcode_val  = params.get("postcode",     [None])[0]
                light_vals    = params.get("light",        [])
                atmo_vals     = params.get("atmo",         [])
                road_vals     = params.get("road",         [])
                year_from_val = params.get("year_from",    [None])[0]
                year_to_val   = params.get("year_to",      [None])[0]
                year_excl     = params.get("year_exclude", [])

                data = get_accident_analysis(
                    postcode     = postcode_val  if postcode_val  else None,
                    light        = light_vals    if light_vals    else None,
                    atmo         = atmo_vals     if atmo_vals     else None,
                    road         = road_vals     if road_vals     else None,
                    year_from    = year_from_val if year_from_val else None,
                    year_to      = year_to_val   if year_to_val   else None,
                    year_exclude = year_excl     if year_excl     else None,
                )

                self.send_json(data)

            except Exception as e:
                print(f"❌ API SERVER ERROR: {e}")
                self.send_json({
                    "error": str(e),
                    "table": [],
                    "pie":  {"labels": [], "values": []},
                    "line": {"labels": [], "values": []}
                })

        else:
            self.send_error(404, "Not found")

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def handle_simple_page(self, title, template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            content_html = f.read()
        full_html = render_page(title, content_html)
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(full_html.encode("utf-8"))

    def handle_static(self, path):
        file_path = path.lstrip("/")
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1]
            content_type = MIME.get(ext, "application/octet-stream")
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-type", content_type)
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, "Static file not found")

    def log_message(self, format, *args):
        pass


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    server_address = ("", 8000)
    httpd = ThreadedHTTPServer(server_address, RequestHandler)
    print("Server running at http://localhost:8000")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()