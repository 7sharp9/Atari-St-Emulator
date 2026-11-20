"""Sum a census_gNNN.jsonl by the wave word read at each chunk's end (chunk attributed to the wave at its end).
    python3 summarize.py <game NNN>"""
import json, os, sys, collections
import bh
W = bh.BW
