# coding=utf-8
from __future__ import absolute_import, unicode_literals

import octoprint.plugin
from octoprint.util import RepeatedTimer
from nut2 import PyNUTClient, PyNUTError
import flask


class UPSState(object):
	UNKNOWN_STATUS = "UNK"
	UNKNOWN_INT = -1

	def __init__(self, raw_state=None):
		self._raw_state = raw_state or {}
		self._state = None
		self._normalize()

	def _normalize(self):
		status = self.UNKNOWN_STATUS

		if "ups.status" in self._raw_state:
			s = self._raw_state["ups.status"]
			# Online flag set
			if "OL" in s:
				status = "OL"
			# On battery flag set
			elif "OB" in s:
				status = "OB"
			else:
				status = self.UNKNOWN_STATUS

		charge = int(self._raw_state.get("battery.charge", self.UNKNOWN_INT))
		runtime = int(self._raw_state.get("battery.runtime", self.UNKNOWN_INT))

		self._state = {
			"status": status,
			"charge": charge,
			"runtime": runtime,
		}

	def __str__(self):
		return str(self.as_dict())

	@property
	def status(self):
		return self._state['status']

	@property
	def charge(self):
		return self._state['charge']

	@property
	def runtime(self):
		return self._state['runtime']

	@property
	def is_unknown(self):
		return self._state["status"] == self.UNKNOWN_STATUS

	def update_raw_state(self, raw_state):
		self._raw_state = raw_state
		self._normalize()

	def raw_state(self):
		return self._raw_state

	def as_dict(self):
		return self._state


class UninterruptiblePlugin(octoprint.plugin.SimpleApiPlugin,
							octoprint.plugin.AssetPlugin,
							octoprint.plugin.TemplatePlugin,
							octoprint.plugin.StartupPlugin,
							octoprint.plugin.SettingsPlugin):

	def __init__(self):
		self._updateTimer = None
		self._state = UPSState()

	##~~ SettingsPlugin

	def get_settings_defaults(self):
		return dict(
			# put your plugin's default settings here
		)

	# ~~ SimpleApiPlugin

	def on_api_get(self, request):
		self._logger.debug("API call received")
		return flask.jsonify(self._state.as_dict())

	##~~ AssetPlugin

	def get_assets(self):
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

	def _update_state_interval(self):
		return 5

	def _update_state(self):
		raw_state = self._get_raw_state_nut()
		state = UPSState(raw_state)
		self._logger.debug("Current state: " + str(state))
		self._plugin_manager.send_plugin_message(self._identifier, state.as_dict())

		if self._state and not self._state.is_unknown and not state.is_unknown and (self._state.status != state.status):
			self._logger.debug("Firing UPS status change event")
			self._event_bus.fire(octoprint.events.Events.PLUGIN_UNINTERRUPTIBLE_UPS_STATUS_CHANGE, state.as_dict())

		self._state = state

	def _get_raw_state_nut(self):
		self._logger.debug("Updating UPS state from NUT")
		try:
			client = PyNUTClient()
			ups = list(client.list_ups().keys())[0]
			data = client.list_vars(ups)
			return data
		except PyNUTError as e:
			self._logger.warning("Error updating UPS state from NUT: " + repr(e))
			return None


def register_custom_events(*args, **kwargs):
	return ["ups_status_change", ]


def __plugin_check__():
	return True


__plugin_pythoncompat__ = ">=2.7,<4"  # python 2 and 3


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = UninterruptiblePlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.events.register_custom_events": register_custom_events,
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
