{
	"patcher": {
		"fileversion": 1,
		"appversion": {
			"major": 8,
			"minor": 6,
			"revision": 5,
			"architecture": "x64",
			"modernui": 1
		},
		"classnamespace": "box",
		"rect": [
			100,
			100,
			320,
			340
		],
		"openinpresentation": 1,
		"boxes": [
			{
				"box": {
					"id": "obj-scale",
					"maxclass": "newobj",
					"numinlets": 6,
					"numoutlets": 1,
					"patching_rect": [
						20,
						110,
						110,
						22
					],
					"outlettype": [
						""
					],
					"text": "scale 0 127 0. 1."
				}
			},
			{
				"box": {
					"id": "obj-split",
					"maxclass": "newobj",
					"numinlets": 3,
					"numoutlets": 2,
					"patching_rect": [
						20,
						140,
						80,
						22
					],
					"outlettype": [
						"",
						""
					],
					"text": "split 0. 0.5"
				}
			},
			{
				"box": {
					"id": "obj-off",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						20,
						170,
						30,
						22
					],
					"outlettype": [
						""
					],
					"text": "0"
				}
			},
			{
				"box": {
					"id": "obj-on",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						80,
						170,
						30,
						22
					],
					"outlettype": [
						""
					],
					"text": "1"
				}
			},
			{
				"box": {
					"id": "obj-set",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						160,
						170,
						70,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend set"
				}
			},
			{
				"box": {
					"id": "obj-button",
					"maxclass": "live.text",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						160,
						210,
						16,
						16
					],
					"outlettype": [
						"",
						""
					],
					"parameter_enable": 1,
					"mode": 1,
					"text": "",
					"texton": "",
					"varname": "on_button",
					"ignoreclick": 1,
					"presentation": 1,
					"presentation_rect": [
						0,
						0,
						16,
						16
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "On Button",
							"parameter_shortname": "On",
							"parameter_type": 2,
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1,
							"parameter_invisible": 2
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-param",
					"maxclass": "live.toggle",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						20,
						70,
						16,
						16
					],
					"outlettype": [
						""
					],
					"parameter_enable": 1,
					"varname": "on",
					"presentation": 1,
					"presentation_rect": [
						0,
						0,
						16,
						16
					],
					"bgcolor": [
						0.0,
						0.0,
						0.0,
						0.0
					],
					"bgoncolor": [
						0.0,
						0.0,
						0.0,
						0.0
					],
					"activebgcolor": [
						0.0,
						0.0,
						0.0,
						0.0
					],
					"activebgoncolor": [
						0.0,
						0.0,
						0.0,
						0.0
					],
					"bordercolor": [
						0.0,
						0.0,
						0.0,
						0.0
					],
					"focusbordercolor": [
						0.0,
						0.0,
						0.0,
						0.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "On",
							"parameter_shortname": "On",
							"parameter_type": 1,
							"parameter_mmin": 0,
							"parameter_mmax": 127,
							"parameter_initial": [
								0
							],
							"parameter_initial_enable": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-print-param",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						240,
						70,
						120,
						22
					],
					"text": "print on-param"
				}
			},
			{
				"box": {
					"id": "obj-print-out",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						240,
						170,
						120,
						22
					],
					"text": "print on-out"
				}
			},
			{
				"box": {
					"id": "obj-in",
					"maxclass": "inlet",
					"numinlets": 0,
					"numoutlets": 1,
					"patching_rect": [
						20,
						20,
						30,
						30
					],
					"outlettype": [
						""
					],
					"comment": "0-127 sets the toggle"
				}
			},
			{
				"box": {
					"id": "obj-out",
					"maxclass": "outlet",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						20,
						290,
						30,
						30
					],
					"comment": "0 off, 1 on"
				}
			}
		],
		"lines": [
			{
				"patchline": {
					"source": [
						"obj-param",
						0
					],
					"destination": [
						"obj-scale",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-scale",
						0
					],
					"destination": [
						"obj-split",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-split",
						0
					],
					"destination": [
						"obj-off",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-split",
						1
					],
					"destination": [
						"obj-on",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-off",
						0
					],
					"destination": [
						"obj-set",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-on",
						0
					],
					"destination": [
						"obj-set",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-set",
						0
					],
					"destination": [
						"obj-button",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-param",
						0
					],
					"destination": [
						"obj-print-param",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-off",
						0
					],
					"destination": [
						"obj-print-out",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-on",
						0
					],
					"destination": [
						"obj-print-out",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-in",
						0
					],
					"destination": [
						"obj-param",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-off",
						0
					],
					"destination": [
						"obj-out",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-on",
						0
					],
					"destination": [
						"obj-out",
						0
					]
				}
			}
		],
		"parameters": {
			"obj-param": [
				"On",
				"On",
				0
			],
			"obj-button": [
				"On Button",
				"On",
				0
			],
			"inherited_shortname": 1
		},
		"autosave": 0
	}
}
