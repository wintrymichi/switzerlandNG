"""Switzerland Builder: a local web app that builds a BeamNG.drive level of any part of Switzerland with the
magliasinaNG pipeline (beamng/pipeline), from open data only. See the README of wintrymichi/switzerlandNG."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BUILDER = os.path.dirname(HERE)                      # beamng/builder
BEAMNG = os.path.dirname(BUILDER)                    # beamng (pipeline, dati, ticino/dati)
REPO = os.path.dirname(BEAMNG)
VERSION = "1.0.0"
