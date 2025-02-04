# 25.01.31 16:30 수정판
from mypackage import gui
import mypackage.check_version as check_version

if __name__ == "__main__":
    check_version.main()
    gui.run_app()