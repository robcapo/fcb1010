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
									"code": "// Klone: a Klon Centaur style overdrive for gen~.\n// Signal levels are treated as volts: 1.0 (0 dBFS) = 1 V peak.\n// Keep this file in step with reference.py, which mirrors it for testing.\n\nParam p_gain(5, min=0, max=10);\nParam p_treble(5, min=0, max=10);\nParam p_output(5, min=0, max=10);\n\n// One-pole lowpass, topology-preserving transform (zero-delay feedback).\nlp1(x, fc) {\n\tHistory z(0);\n\tg = tan(pi * fc / samplerate);\n\tv = (x - z) * g / (1 + g);\n\ty = v + z;\n\tz = y + v;\n\treturn y;\n}\n\n// One-pole lowpass with a fixed cutoff; used as a parameter smoother.\nsmoother(x, coeff) {\n\tHistory s(0);\n\ts = s + (x - s) * coeff;\n\treturn s;\n}\n\n// Germanium diode pair to ground (1N34A), modelled as x / sqrt(1 + x^2)\n// with first-order antiderivative anti-aliasing. The antiderivative is\n// sqrt(1 + x^2), and (F(u) - F(u1)) / (u - u1) simplifies exactly to\n// (u + u1) / (F(u) + F(u1)), so there is no divide-by-zero case.\ndiodes(x, vf) {\n\tHistory u1(0);\n\tu = x / vf;\n\ty = (u + u1) / (sqrt(1 + u * u) + sqrt(1 + u1 * u1));\n\tu1 = u;\n\treturn y * vf;\n}\n\n// Audio-taper pot law: 0 at 0, 1 at 1, about 15% at noon.\naudio_taper(t) {\n\treturn (pow(30, t) - 1) / 29;\n}\n\nchannel(x, gain_t, treble_db, out_amp) {\n\t// Input buffer coupling caps.\n\txin = x - lp1(x, 16);\n\n\t// Clipping stage: the gain is applied to content above about 400 Hz\n\t// and the feedback cap closes the top end in as gain goes up, which\n\t// is where the mid hump comes from.\n\ttaper = audio_taper(gain_t);\n\thp = xin - lp1(xin, 400);\n\tpre = xin + 120 * taper * hp;\n\tpre = lp1(pre, 12000 / (1 + 3 * taper));\n\tdirty = diodes(pre, 0.35);\n\n\t// Dual-gang gain pot: the second gang turns the clean path down as\n\t// the first turns the gain up, but never all the way off.\n\tclean = xin * (1 - 0.9 * gain_t);\n\n\t// Summing amp: the clipped path goes in at twice the weight of the clean\n\t// one, and the feedback cap rolls off the fizz.\n\tsummed = lp1(clean + 2 * dirty, 6500);\n\n\t// Treble: active first-order high shelf around 1.2 kHz.\n\tlo = lp1(summed, 1200);\n\ttoned = lo + dbtoa(treble_db) * (summed - lo);\n\n\t// Output volume, then the output coupling cap.\n\ty = toned * out_amp;\n\treturn y - lp1(y, 8);\n}\n\n// 20 ms parameter smoothing.\nk = 1 - exp(-1 / (0.02 * samplerate));\ngain_t = smoother(p_gain / 10, k);\ntreble_db = smoother((p_treble - 5) * 2.4, k);\nout_amp = smoother(2.2 * audio_taper(p_output / 10), k);\n\nout1 = channel(in1, gain_t, treble_db, out_amp);\nout2 = channel(in2, gain_t, treble_db, out_amp);\n",
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
