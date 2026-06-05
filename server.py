
from http.server import BaseHTTPRequestHandler, HTTPServer
import sqlite3
import os
import json
import urllib.parse


# ---- Level 1: Home & About -----

# ---- Level 2: People & Injury + Accident Condition ----
from Level2_db import injury_summary, pictogram_data, ejected_hospital_table, \
    get_age_groups, get_injury_levels, get_road_user_types, get_light_conditions

# ---- Level 3: People Analysis + Accident Analysis ----
from Level3_db import people_analysis, people_analysis_chart

MIME = {
    ".css" : "text/css", ".js" : "application/javascript",
    ".png" : "image/png", ".jpg" : "image/jpeg",
    ".ico" : "image/x-icon", ".svg" : "image/svg+xml",
}

print("LOADING SERVER CODE")
#DB_NAME = "database/Road_Accidents.db"

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
        
        # --- API level 1 --- 
       
        elif path == "/api/home":
            from Level1_db import get_home_stats
            self.send_json(get_home_stats())
           

        elif path == "/api/about":
            self.send_json({})
           
        # --- API Level2 ---
        elif path == "/api/injury-summary":
            levels = [int(x) for x in params.get("level", [])]
            self.send_json(injury_summary(levels or None))
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
            from Level2_db import get_age_groups, get_injury_levels, get_road_user_types, get_light_conditions
            self.send_json({
                "age_groups":       get_age_groups(),
                "injury_levels":    get_injury_levels(),
                "person_types":     get_road_user_types(),
                "light_conditions": get_light_conditions(),
            })

        # ---- API: Level 3 ----
        elif path == "/api/people-analysis":
            filters = {k: v for k, v in {
                "level": params.get("level", []),
                "age":   params.get("age", []),
                "light": params.get("light", []),
            }.items() if v}
            self.send_json({
                "table": people_analysis(filters),
                "chart": people_analysis_chart(filters),
            })
        
        else:
            self.send_error(404, "Not found")

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
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


def run():
    server_address = ("", 8000)  # localhost:8000
    httpd = HTTPServer(server_address, RequestHandler)
    print("Server running at http://localhost:8000")
    httpd.serve_forever()


if __name__ == "__main__":
    run()