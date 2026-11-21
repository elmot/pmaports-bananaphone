#!/usr/bin/env python3
import os
import slint

HERE = os.path.dirname(os.path.abspath(__file__))
app = slint.load_file(os.path.join(HERE, "main.slint"))
win = app.Demo()
win.run()
