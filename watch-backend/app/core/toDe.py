from pathlib import Path
import os

# backend_root = Path(__file__).parent.parent.parent
# video_id = "SYia4zqcE4g"
# lan_code = "abc"
# output_file_path = str(backend_root) + "/static/" + video_id + "/" + video_id + "." + lan_code + ".vtt"
# print("vtt output_file_path: ", output_file_path)
p = "/Users/qin/Documents/GitHub/MAcode/watch-backend/static/SYia4zqcE4g/SYia4zqcE4g.zh-CN.vtt"
with open(Path(p), "w", encoding="utf-8") as f:
    print(type(f))
    f.write("abc")

