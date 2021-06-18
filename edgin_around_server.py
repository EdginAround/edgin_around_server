#!/usr/bin/env python

import logging
import src

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    src.Server().run()
