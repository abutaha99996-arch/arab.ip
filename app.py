from flask import Flask, request, jsonify, render_template
import requests
import sqlite3
import datetime
import os
import json
import time

app = Flask(__name__)

# إعدادات التلجرام
TELEGRAM_BOT_TOKEN = "8266899631:AAEUxiahvm8gnAreYXVS0Zjj5d153D7Ab-Y"
TELEGRAM_CHAT
