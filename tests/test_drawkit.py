# Drawing Lab smoke tests: run every subcommand in an isolated temp dir.
# Usage:
#   python -X utf8 -B tests/test_drawkit.py
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, "..", "scripts", "drawkit.py")

FAILS = []


def run(args, expect=0):
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-B", KIT] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    ok = proc.returncode == expect
    tag = "ok " if ok else "FAIL"
    if not ok:
        FAILS.append(args)
    print(f"[{tag}] drawkit {' '.join(args)} -> rc={proc.returncode}")
    if not ok:
        for line in (proc.stdout + proc.stderr).strip().splitlines()[-12:]:
            print("     |", line)
    return ok


def main():
    with tempfile.TemporaryDirectory(prefix="drawkit-test-") as tmp:
        return smoke(tmp)


def smoke(tmp):
    print(f"临时目录：{tmp}")
    def p(name):
        return os.path.join(tmp, name)

    source = os.path.join(HERE, "..", "examples", "mindmap.md")
    run(["mindmap", p("map.svg"), "--input", source])
    run(["mindmap", p("map.png"), "--input", source, "--layout", "right", "--scale", "2"])
    run(["doctor"])
    run(["svg", "scenes"])
    run(["svg", "new", p("a.svg"), "--scene", "concentric", "--width", "320", "--height", "320", "--seed", "3"])
    run(["svg", "new", p("b.svg"), "--scene", "mountains", "--width", "320", "--height", "200", "--seed", "3"])
    run(["svg", "new", p("c.svg"), "--scene", "waves", "--width", "320", "--height", "200", "--seed", "3"])
    run(["svg", "new", p("d.svg"), "--scene", "skyline", "--width", "320", "--height", "200", "--seed", "3"])
    run(["svg", "new", p("e.svg"), "--scene", "grid", "--width", "320", "--height", "200", "--seed", "3"])
    run(["svg", "new", p("f.svg"), "--scene", "spiral", "--width", "320", "--height", "200", "--seed", "3"])
    run(["svg", "check", p("a.svg")])
    run(["svg", "render", p("a.svg"), "-o", p("a.png")])
    assert os.path.isfile(p("a.png"))

    for scene in ["gradient", "stripes", "checker", "dots", "rings", "waves",
                  "blobs", "stars", "sunburst", "city", "spiral"]:
        run(["raster", p(f"r-{scene}.png"), "--scene", scene, "--width", "240", "--height", "160", "--seed", "5"])
        assert os.path.isfile(p(f"r-{scene}.png")), scene

    run(["chart", "bar", p("c-bar.png"), "--values", "12,30,22,40", "--labels", "a,b,c,d", "--title", "t"])
    run(["chart", "hbar", p("c-hbar.png"), "--values", "1,2,3"])
    run(["chart", "line", p("c-line.png"), "--values", "5,8,6,12", "--theme", "dark"])
    run(["chart", "pie", p("c-pie.png"), "--values", "30,20,50", "--labels", "A,B,C"])
    run(["chart", "scatter", p("c-scatter.png"), "--pairs", "1:2,2:3,3:1,4:5"])

    run(["ascii", "render", p("r-sunburst.png"), "-o", p("art.txt"), "--cols", "40"])
    assert os.path.isfile(p("art.txt"))
    run(["ascii", "render", p("r-sunburst.png"), "-o", p("art-bw.txt"), "--cols", "40", "--threshold", "128"])
    run(["ascii", "toimage", p("art.txt"), "-o", p("art.png"), "--size", "12"])
    assert os.path.isfile(p("art.png"))

    src = p("r-city.png")
    run(["photo", "info", src])
    run(["photo", "inspect", src])
    run(["photo", "edit", src, "-o", p("edit1.png"), "--op", "rotate=90", "--op", "resize=200x"])
    run(["photo", "edit", src, "-o", p("edit2.png"), "--op", "sepia", "--op", "vignette=40"])
    run(["photo", "edit", src, "-o", p("edit3.jpg"), "--op", "crop=10%,10%,80%,80%", "--op", "brightness=1.1", "--format", "jpg"])
    run(["photo", "canvas", p("edit1.png"), p("edit2.png"), src, "-o", p("grid.png"), "--cols", "3"])
    run(["photo", "blend", p("edit1.png"), src, "-o", p("blend.png"), "--mix", "0.5"])
    run(["photo", "blend", p("edit1.png"), src, "-o", p("blend-h.png"), "--mask", "h"])
    run(["photo", "text", src, "-o", p("tagged.png"), "--text", "City\n2026", "--pos", "bottom", "--size", "32"])
    run(["photo", "text", "-o", p("poster.png"), "--text", "海报标题", "--blank", "--width", "600", "--height", "400", "--size", "48", "--color", "#f72585", "--background", "#0d0221"])

    run(["physics", "circuit", p("circuit.png"), "--spec", "B:(140,120)-(140,420);W:(140,120)-(420,120);R:(420,120)-(420,250);L:(420,250)-(420,420);W:(420,420)-(140,420)"])
    run(["physics", "ray", p("ray-convex.png"), "--kind", "convex", "--focal", "90", "--object", "150", "--height", "60"])
    run(["physics", "ray", p("ray-plane.png"), "--kind", "plane", "--object", "120", "--height", "60"])
    run(["physics", "force", p("force.png"), "--angle", "30", "--friction", "--free", "--cn"])
    run(["physics", "object", p("incline.png"), "--scene", "incline", "--angle", "35", "--cn"])
    run(["physics", "object", p("wave.png"), "--scene", "wave", "--amplitude", "40", "--wavelength", "100", "--cycles", "2", "--cn"])
    run(["math", "figure", p("figure.png"), "--spec", "pt A 90,470;pt B 730,470;pt C 410,150;line A-B;line B-C;line C-A;mid M A B;aux C-M;right C A B;ang A C B 45;eq A-C B-C;dot A B C M", "--dots"])
    run(["math", "func", p("func.png"), "--fn", "x**2-2", "--xmin", "-4", "--xmax", "4", "--tangent", "1.5", "--roots", "--grid", "--axis-labels"])
    run(["math", "axes", p("axes.png"), "--grid"])

    run(["3d", p("cube.png"), "--scene", "cube"])
    run(["3d", p("sphere.png"), "--scene", "sphere"])
    run(["chem", "molecule", p("mol.png"), "--atoms", "C:260,260;O:390,260;H1:210,180;H2:310,180", "--bonds", "C:O:1;C:H1:1;C:H2:1"])
    run(["chem", "cell", p("bcc.png"), "--kind", "bcc"])
    run(["chem", "reaction", p("reaction.png"), "--equation", "2H2+O2->2H2O"])
    run(["chem", "apparatus", p("beaker.png"), "--kind", "beaker"])

    if FAILS:
        print(f"\n{len(FAILS)} 项失败：{FAILS}")
        return 1
    print("\n全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
