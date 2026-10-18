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
			640,
			480
		],
		"openinpresentation": 1,
		"default_fontsize": 10.0,
		"default_fontname": "Arial Bold",
		"gridsize": [
			8.0,
			8.0
		],
		"devicewidth": 170.0,
		"description": "Klon Centaur style overdrive",
		"boxes": [
			{
				"box": {
					"id": "obj-plugin",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						20,
						20,
						53,
						22
					],
					"outlettype": [
						"signal",
						"signal"
					],
					"text": "plugin~"
				}
			},
			{
				"box": {
					"id": "obj-gen",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						20,
						200,
						110,
						22
					],
					"outlettype": [
						"signal",
						"signal"
					],
					"text": "gen~ @title klone",
					"patcher": {
						"fileversion": 1,
						"appversion": {
							"major": 8,
							"minor": 6,
							"revision": 5,
							"architecture": "x64",
							"modernui": 1
						},
						"classnamespace": "dsp.gen",
						"rect": [
							100,
							100,
							660,
							840
						],
						"boxes": [
							{
								"box": {
									"id": "obj-1",
									"maxclass": "newobj",
									"numinlets": 0,
									"numoutlets": 1,
									"patching_rect": [
										20,
										20,
										30,
										22
									],
									"outlettype": [
										""
									],
									"text": "in 1"
								}
							},
							{
								"box": {
									"id": "obj-2",
									"maxclass": "newobj",
									"numinlets": 0,
									"numoutlets": 1,
									"patching_rect": [
										400,
										20,
										30,
										22
									],
									"outlettype": [
										""
									],
									"text": "in 2"
								}
							},
							{
								"box": {
									"id": "obj-3",
									"maxclass": "codebox",
									"numinlets": 2,
									"numoutlets": 2,
									"patching_rect": [
										20,
										60,
										600,
										700
									],
									"outlettype": [
										"",
										""
									],
									"code": "// Klone: a Klon Centaur style overdrive for gen~.\n// Signal levels are treated as volts: 1.0 (0 dBFS) = 1 V peak.\n// Keep this file in step with reference.py, which mirrors it for testing.\n//\n// This is a template: build.py copies everything between the CHANNEL\n// markers, and every other line containing @, once per channel, replacing\n// @ with the channel number. The code uses no user functions, so every\n// filter's state is an explicit History.\n\nParam p_gain(5, min=0, max=10);\nParam p_treble(5, min=0, max=10);\nParam p_output(5, min=0, max=10);\n\nHistory s_gain(0.5);\nHistory s_treble(0);\nHistory s_output(0.33);\nHistory z_in1(0);\nHistory z_in2(0);\nHistory z_hp1(0);\nHistory z_hp2(0);\nHistory z_pre1(0);\nHistory z_pre2(0);\nHistory z_sum1(0);\nHistory z_sum2(0);\nHistory z_tone1(0);\nHistory z_tone2(0);\nHistory z_out1(0);\nHistory z_out2(0);\nHistory u1_1(0);\nHistory u1_2(0);\n\n// 20 ms parameter smoothing.\nk = 1 - exp(-1 / (0.02 * samplerate));\ns_gain = s_gain + (p_gain / 10 - s_gain) * k;\ns_treble = s_treble + ((p_treble - 5) * 2.4 - s_treble) * k;\n// Audio-taper pot law: 0 at 0, 1 at 1, about 15% at noon.\ns_output = s_output + (2.2 * (pow(30, p_output / 10) - 1) / 29 - s_output) * k;\n\ngain_t = s_gain;\ntaper = (pow(30, gain_t) - 1) / 29;\ntreble_amp = dbtoa(s_treble);\nout_amp = s_output;\n\n// One-pole TPT lowpass coefficients, G = g / (1 + g) with g = tan(pi fc / sr).\n// Each filter below is: v = (x - z) * G; y = v + z; z = y + v.\ng = tan(pi * 16 / samplerate);\nc_in = g / (1 + g);\ng = tan(pi * 400 / samplerate);\nc_hp = g / (1 + g);\n// The clipping stage's feedback cap closes the top end in as gain goes up.\ng = tan(pi * 12000 / (1 + 3 * taper) / samplerate);\nc_pre = g / (1 + g);\ng = tan(pi * 6500 / samplerate);\nc_sum = g / (1 + g);\ng = tan(pi * 1200 / samplerate);\nc_tone = g / (1 + g);\ng = tan(pi * 8 / samplerate);\nc_out = g / (1 + g);\n\n// Channel 1\n// Input buffer coupling caps.\nv = (in1 - z_in1) * c_in;\nlp = v + z_in1;\nz_in1 = lp + v;\nxin1 = in1 - lp;\n\n// Clipping stage: the gain is applied to content above about 400 Hz,\n// which with the feedback cap gives the dirty path its mid hump.\nv = (xin1 - z_hp1) * c_hp;\nlp = v + z_hp1;\nz_hp1 = lp + v;\npre1 = xin1 + 120 * taper * (xin1 - lp);\nv = (pre1 - z_pre1) * c_pre;\nlp = v + z_pre1;\nz_pre1 = lp + v;\n\n// Germanium diode pair to ground (1N34A), modelled as x / sqrt(1 + x^2)\n// with first-order antiderivative anti-aliasing. The antiderivative is\n// sqrt(1 + x^2), and (F(u) - F(u1)) / (u - u1) simplifies exactly to\n// (u + u1) / (F(u) + F(u1)), so there is no divide-by-zero case.\nu = lp / 0.35;\ndirty1 = 0.35 * (u + u1_1) / (sqrt(1 + u * u) + sqrt(1 + u1_1 * u1_1));\nu1_1 = u;\n\n// Dual-gang gain pot: the second gang turns the clean path down as\n// the first turns the gain up, but never all the way off.\nclean1 = xin1 * (1 - 0.9 * gain_t);\n\n// Summing amp: the clipped path goes in at twice the weight of the clean\n// one, and the feedback cap rolls off the fizz.\nx = clean1 + 2 * dirty1;\nv = (x - z_sum1) * c_sum;\nsummed1 = v + z_sum1;\nz_sum1 = summed1 + v;\n\n// Treble: active first-order high shelf around 1.2 kHz.\nv = (summed1 - z_tone1) * c_tone;\nlp = v + z_tone1;\nz_tone1 = lp + v;\ny = (lp + treble_amp * (summed1 - lp)) * out_amp;\n\n// Output volume, then the output coupling cap.\nv = (y - z_out1) * c_out;\nlp = v + z_out1;\nz_out1 = lp + v;\nout1 = y - lp;\n\n// Channel 2\n// Input buffer coupling caps.\nv = (in2 - z_in2) * c_in;\nlp = v + z_in2;\nz_in2 = lp + v;\nxin2 = in2 - lp;\n\n// Clipping stage: the gain is applied to content above about 400 Hz,\n// which with the feedback cap gives the dirty path its mid hump.\nv = (xin2 - z_hp2) * c_hp;\nlp = v + z_hp2;\nz_hp2 = lp + v;\npre2 = xin2 + 120 * taper * (xin2 - lp);\nv = (pre2 - z_pre2) * c_pre;\nlp = v + z_pre2;\nz_pre2 = lp + v;\n\n// Germanium diode pair to ground (1N34A), modelled as x / sqrt(1 + x^2)\n// with first-order antiderivative anti-aliasing. The antiderivative is\n// sqrt(1 + x^2), and (F(u) - F(u1)) / (u - u1) simplifies exactly to\n// (u + u1) / (F(u) + F(u1)), so there is no divide-by-zero case.\nu = lp / 0.35;\ndirty2 = 0.35 * (u + u1_2) / (sqrt(1 + u * u) + sqrt(1 + u1_2 * u1_2));\nu1_2 = u;\n\n// Dual-gang gain pot: the second gang turns the clean path down as\n// the first turns the gain up, but never all the way off.\nclean2 = xin2 * (1 - 0.9 * gain_t);\n\n// Summing amp: the clipped path goes in at twice the weight of the clean\n// one, and the feedback cap rolls off the fizz.\nx = clean2 + 2 * dirty2;\nv = (x - z_sum2) * c_sum;\nsummed2 = v + z_sum2;\nz_sum2 = summed2 + v;\n\n// Treble: active first-order high shelf around 1.2 kHz.\nv = (summed2 - z_tone2) * c_tone;\nlp = v + z_tone2;\nz_tone2 = lp + v;\ny = (lp + treble_amp * (summed2 - lp)) * out_amp;\n\n// Output volume, then the output coupling cap.\nv = (y - z_out2) * c_out;\nlp = v + z_out2;\nz_out2 = lp + v;\nout2 = y - lp;\n",
									"fontface": 0,
									"fontname": "<Monospaced>",
									"fontsize": 12
								}
							},
							{
								"box": {
									"id": "obj-4",
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										20,
										780,
										37,
										22
									],
									"text": "out 1"
								}
							},
							{
								"box": {
									"id": "obj-5",
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										400,
										780,
										37,
										22
									],
									"text": "out 2"
								}
							}
						],
						"lines": [
							{
								"patchline": {
									"source": [
										"obj-1",
										0
									],
									"destination": [
										"obj-3",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-2",
										0
									],
									"destination": [
										"obj-3",
										1
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-3",
										0
									],
									"destination": [
										"obj-4",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-3",
										1
									],
									"destination": [
										"obj-5",
										0
									]
								}
							}
						]
					}
				}
			},
			{
				"box": {
					"id": "obj-plugout",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 0,
					"patching_rect": [
						20,
						260,
						60,
						22
					],
					"text": "plugout~"
				}
			},
			{
				"box": {
					"id": "obj-title",
					"maxclass": "comment",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						300,
						20,
						120,
						20
					],
					"text": "KLONE",
					"presentation": 1,
					"presentation_rect": [
						8,
						4,
						150,
						20
					],
					"fontsize": 13,
					"fontface": 1
				}
			},
			{
				"box": {
					"id": "obj-dial-0",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						160,
						60,
						44,
						48
					],
					"outlettype": [
						"",
						"float"
					],
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						8,
						40,
						44,
						48
					],
					"varname": "Gain",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Gain",
							"parameter_shortname": "Gain",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 10.0,
							"parameter_initial": [
								5.0
							],
							"parameter_initial_enable": 1,
							"parameter_unitstyle": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-prepend-0",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						160,
						130,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend p_gain"
				}
			},
			{
				"box": {
					"id": "obj-dial-1",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						270,
						60,
						44,
						48
					],
					"outlettype": [
						"",
						"float"
					],
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						62,
						40,
						44,
						48
					],
					"varname": "Treble",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Treble",
							"parameter_shortname": "Treble",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 10.0,
							"parameter_initial": [
								5.0
							],
							"parameter_initial_enable": 1,
							"parameter_unitstyle": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-prepend-1",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						270,
						130,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend p_treble"
				}
			},
			{
				"box": {
					"id": "obj-dial-2",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						380,
						60,
						44,
						48
					],
					"outlettype": [
						"",
						"float"
					],
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						116,
						40,
						44,
						48
					],
					"varname": "Output",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Output",
							"parameter_shortname": "Output",
							"parameter_type": 0,
							"parameter_mmin": 0.0,
							"parameter_mmax": 10.0,
							"parameter_initial": [
								5.0
							],
							"parameter_initial_enable": 1,
							"parameter_unitstyle": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-prepend-2",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						380,
						130,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend p_output"
				}
			}
		],
		"lines": [
			{
				"patchline": {
					"source": [
						"obj-plugin",
						0
					],
					"destination": [
						"obj-gen",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-plugin",
						1
					],
					"destination": [
						"obj-gen",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-gen",
						0
					],
					"destination": [
						"obj-plugout",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-gen",
						1
					],
					"destination": [
						"obj-plugout",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-dial-0",
						0
					],
					"destination": [
						"obj-prepend-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-0",
						0
					],
					"destination": [
						"obj-gen",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-dial-1",
						0
					],
					"destination": [
						"obj-prepend-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-1",
						0
					],
					"destination": [
						"obj-gen",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-dial-2",
						0
					],
					"destination": [
						"obj-prepend-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-2",
						0
					],
					"destination": [
						"obj-gen",
						0
					]
				}
			}
		],
		"parameters": {
			"obj-dial-0": [
				"Gain",
				"Gain",
				0
			],
			"obj-dial-1": [
				"Treble",
				"Treble",
				0
			],
			"obj-dial-2": [
				"Output",
				"Output",
				0
			],
			"inherited_shortname": 1
		},
		"dependency_cache": [],
		"autosave": 0
	}
}
