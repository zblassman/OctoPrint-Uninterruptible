# coding=utf-8
from __future__ import absolute_import, unicode_literals

import octoprint.plugin
from octoprint.util import RepeatedTimer
from nut2 import PyNUTClient, PyNUTError
import flask

class UninterruptiblePlugin(octoprint.plugin.SimpleApiPlugin,
							octoprint.plugin.AssetPlugin,
							octoprint.plugin.TemplatePlugin,
							octoprint.plugin.StartupPlugin,
							octoprint.plugin.SettingsPlugin):

	UNKNOWN_STATE = {"UNK", -1, -1}

	def __init__(self):
		self._updateTimer = None
		self._state = None

	##~~ SettingsPlugin

	def get_settings_defaults(self):
		return dict(
			# put your plugin's default settings here
		)

	#~~ SimpleApiPlugin

	def on_api_get(self, request):
		self._logger.debug("API call received")
		state = self._get_state()
		return flask.jsonify(state)

	##~~ AssetPlugin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/uninterruptible.js"],
			clientjs=["clientjs/uninterruptible.js"],
			css=["css/uninterruptible.css"],
			less=["less/uninterruptible.less"]
		)

	##~~ TemplatePlugin

	def get_template_configs(self):
		return [
			{
				"type": "navbar",
				"custom_bindings": True,
				"classes": [
					"dropdown",
				],
			},
			{
				"type": "settings",
				"custom_bindings": False,
			},
		]

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
		# for details.
		return dict(
			uninterruptible=dict(
				displayName="Uninterruptible Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="zblassman",
				repo="OctoPrint-Uninterruptible",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/zblassman/OctoPrint-Uninterruptible/archive/{target_version}.zip"
			)
		)

	##~~ StartupPlugin

	def on_after_startup(self):
		self._update_timer = RepeatedTimer(self._update_state_interval, self._update_state)
		self._update_timer.start()

	def _get_state(self):
		if not self._state:
			self._update_state()
		return self._state or self.UNKNOWN_STATE

	def _update_state_interval(self):
		return 10

	def _update_state(self):
		state = self._get_state_nut()
		self._logger.debug("Current state: " + str(state))
		self._plugin_manager.send_plugin_message(self._identifier, state)

		if self._state and self._state["status"] != state["status"]:
			self._logger.debug("Firing UPS status change event")
			self._event_bus.fire(octoprint.events.Events.PLUGIN_UNINTERRUPTIBLE_UPS_STATUS_CHANGE, state)

		self._state = state

	def _get_state_test(self):
		self._logger.debug("Updating UPS state with test values")
		return { "status": "OL", "charge": 98, "runtime": 3600 }

	def _get_state_nut(self):
		self._logger.debug("Updating UPS state from NUT")
		try:
			client = PyNUTClient()
			ups = list(client.list_ups().keys())[0]
			data = client.list_vars(ups)
		except PyNUTError as e:
			self._logger.warning("Error updating UPS state from NUT: " + repr(e))
			return None
		status = data["ups.status"]
		status_norm = "OL" if "OL" in status else "OB"
		return {
			"status": status_norm,
			"charge": int(data.get("battery.charge", -1)),
			"runtime": int(data.get("battery.runtime", -1))
		}

	# def _get_state_apcupsd(self):
	# 	self._logger.debug("Updating UPS state from apcupsd")
	# 	out = subprocess.check_output('apcaccess').decode()

def register_custom_events(*args, **kwargs):
	return ["ups_status_change",]


def __plugin_check__():
	return True

__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = UninterruptiblePlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.events.register_custom_events": register_custom_events,
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

