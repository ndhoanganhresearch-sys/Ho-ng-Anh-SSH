from .common import QtWidgets, sys, QT_IMPORT_ERROR


def main() -> int:
    if QT_IMPORT_ERROR is not None:
        raise SystemExit(QT_IMPORT_ERROR)
    from .ui.main_window import TunnelAnalysisWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Tunnel Analysis v4.0")
    win = TunnelAnalysisWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
