{
	"patcher": {
		"fileversion": 1,
		"appversion": {
			"major": 8,
			"minor": 5,
			"revision": 0,
			"architecture": "x64",
			"modernui": 1
		},
		"classnamespace": "box",
		"rect": [
			100,
			100,
			700,
			400
		],
		"openinpresentation": 1,
		"devicewidth": 170.0,
		"boxes": [
			{
				"box": {
					"id": "obj-1",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						20,
						20,
						60,
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
					"id": "obj-2",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 2,
					"patching_rect": [
						20,
						200,
						300,
						22
					],
					"outlettype": [
						"signal",
						"signal"
					],
					"text": "gen~",
					"patcher": {
						"fileversion": 1,
						"appversion": {
							"major": 8,
							"minor": 5,
							"revision": 0,
							"architecture": "x64",
							"modernui": 1
						},
						"classnamespace": "dsp.gen",
						"rect": [
							100,
							100,
							700,
							650
						],
						"boxes": [
							{
								"box": {
									"id": "in-1",
									"maxclass": "newobj",
									"numinlets": 0,
									"numoutlets": 1,
									"patching_rect": [
										20,
										20,
										40,
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
									"id": "in-2",
									"maxclass": "newobj",
									"numinlets": 0,
									"numoutlets": 1,
									"patching_rect": [
										140,
										20,
										40,
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
									"id": "code",
									"maxclass": "codebox",
									"numinlets": 2,
									"numoutlets": 2,
									"patching_rect": [
										20,
										60,
										600,
										500
									],
									"outlettype": [
										"",
										""
									],
									"code": "// FCB Whammy: a DigiTech Whammy style pitch shifter.\n//\n// in1, in2: audio in (left, right). The shifter runs on their mix, so it's\n//           built for a mono source like a guitar.\n// out1, out2: audio out (left, right)\n//\n// Params:\n//   mode: which preset, 0-20. See the table below.\n//   treadle: the pedal, 0 (heel down) to 127 (toe down).\n//   on: 0 passes the input through untouched, 1 is the effect.\n//\n// Whammy presets sweep from the heel interval to the toe interval with\n// only the shifted signal out, so heel down is the dry sound. Harmony\n// presets do the same but keep the dry signal under the shifted one.\n// Detune presets mix the dry signal with one voice tuned slightly up and\n// one slightly down, and ignore the treadle.\n\nParam mode(1, min = 0, max = 20);\nParam treadle(0, min = 0, max = 127);\nParam on(1, min = 0, max = 1);\n\n// The input, as a ring buffer (about 5 seconds at 48kHz)\nData ring(262144);\n// One row per grain, two grains per voice: delay in samples, age in samples\nData grains(4, 2);\n\nHistory wi(0);\nHistory lastm(-1);\nHistory tsm(0);\nHistory onsm(1);\n\nringsize = dim(ring);\n// The treadle glides like the pedal instead of jumping\ntcoef = exp(-1 / mstosamps(20));\noncoef = exp(-1 / mstosamps(5));\n// How far back to look for a spot that lines up with the grain that's\n// playing. A bit more than the period of a guitar's low E.\nsearch = floor(mstosamps(15));\n// How many samples to compare when lining grains up\ncmplen = 128;\n\nm = floor(mode);\n// kind: 0 whammy, 1 harmony, 2 detune\n// heel and toe are in semitones; for detune, toe is the depth in cents\nkind = 0;\nheel = 0;\ntoe = 0;\nif (m == 0) { toe = 24; }           // 2 Oct Up\nelse if (m == 1) { toe = 12; }      // Oct Up\nelse if (m == 2) { toe = 7; }       // 5th Up\nelse if (m == 3) { toe = 5; }       // 4th Up\nelse if (m == 4) { toe = -2; }      // 2nd Down\nelse if (m == 5) { toe = -5; }      // 4th Down\nelse if (m == 6) { toe = -7; }      // 5th Down\nelse if (m == 7) { toe = -12; }     // Oct Down\nelse if (m == 8) { toe = -24; }     // 2 Oct Down\nelse if (m == 9) { toe = -36; }     // Dive Bomb\nelse if (m == 10) { kind = 2; toe = 25; }  // Deep Detune\nelse if (m == 11) { kind = 2; toe = 10; }  // Shallow Detune\nelse if (m == 12) { kind = 1; heel = -12; toe = 12; } // Oct Down / Oct Up\nelse if (m == 13) { kind = 1; heel = -7; toe = -5; }  // 5th Down / 4th Down\nelse if (m == 14) { kind = 1; heel = -5; toe = -4; }  // 4th Down / 3rd Down\nelse if (m == 15) { kind = 1; heel = 7; toe = 10; }   // 5th Up / 7th Up\nelse if (m == 16) { kind = 1; heel = 7; toe = 9; }    // 5th Up / 6th Up\nelse if (m == 17) { kind = 1; heel = 5; toe = 7; }    // 4th Up / 5th Up\nelse if (m == 18) { kind = 1; heel = 4; toe = 5; }    // 3rd Up / 4th Up\nelse if (m == 19) { kind = 1; heel = 3; toe = 4; }    // b3rd Up / 3rd Up\nelse { kind = 1; heel = 2; toe = 4; }                 // 2nd Up / 3rd Up\n\ntarget = clamp(treadle / 127, 0, 1);\ntsm = target + (tsm - target) * tcoef;\nonsm = on + (onsm - on) * oncoef;\n\n// Ratio of each voice. Voice 2 is only used by detune presets.\nst = heel + (toe - heel) * tsm;\nr1 = pow(2, st / 12);\nr2 = 1;\nnvoices = 1;\nif (kind == 2) {\n\tr1 = pow(2, toe / 1200);\n\tr2 = pow(2, -toe / 1200);\n\tnvoices = 2;\n}\n\n// Grain length. Grains read through about 40ms of input whatever the\n// shift, so high presets get short grains and stay close to real time.\ngrainlen = mstosamps(40) / max(pow(2, max(max(heel, toe), 0) / 12), 1);\n\n// Changing preset restarts the grains half a grain apart\nif (m != lastm) {\n\tfor (g = 0; g < 4; g += 1) {\n\t\tpoke(grains, 4, g, 0);\n\t\tpoke(grains, (g % 2) * grainlen * 0.5, g, 1);\n\t}\n}\nlastm = m;\n\nx = (in1 + in2) * 0.5;\npoke(ring, x, wi, 0);\n\n// Each voice is two overlapping grains with raised cosine windows that sum\n// to one. A grain reads the input back at the voice's ratio, so its delay\n// grows or shrinks over its life. When a grain ends, the next one starts at\n// the delay where the input best lines up with what the other grain is\n// playing, so the two blend without cancelling each other out.\nv1 = 0;\nv2 = 0;\nfor (v = 0; v < nvoices; v += 1) {\n\tr = r1;\n\tif (v == 1) {\n\t\tr = r2;\n\t}\n\t// Shortest delay a grain can start at without reading past the input\n\tdmin = max(r - 1, 0) * grainlen + 4;\n\tvout = 0;\n\tfor (g = 0; g < 2; g += 1) {\n\t\trow = v * 2 + g;\n\t\tdly = peek(grains, row, 0);\n\t\tage = peek(grains, row, 1);\n\t\tif (age >= grainlen) {\n\t\t\tage = 0;\n\t\t\tother = floor(peek(grains, v * 2 + 1 - g, 0));\n\t\t\tbest = dmin;\n\t\t\tbestc = -1e9;\n\t\t\tfor (k = 0; k < search; k += 2) {\n\t\t\t\tcand = floor(dmin) + k;\n\t\t\t\ts = 0;\n\t\t\t\ten = 0.000001;\n\t\t\t\tfor (j = 0; j < cmplen; j += 2) {\n\t\t\t\t\tp = peek(ring, wi - cand - j, 0, boundmode = \"wrap\");\n\t\t\t\t\tq = peek(ring, wi - other - j, 0, boundmode = \"wrap\");\n\t\t\t\t\ts += p * q;\n\t\t\t\t\ten += p * p;\n\t\t\t\t}\n\t\t\t\tcorr = s / sqrt(en);\n\t\t\t\tif (corr > bestc) {\n\t\t\t\t\tbestc = corr;\n\t\t\t\t\tbest = cand;\n\t\t\t\t}\n\t\t\t}\n\t\t\tdly = best;\n\t\t}\n\t\tdly = clamp(dly, 2, ringsize - cmplen - search - 4);\n\t\tw = 0.5 - 0.5 * cos(twopi * age / grainlen);\n\t\tvout += w * peek(ring, wi - dly, 0, interp = \"cubic\", boundmode = \"wrap\");\n\t\tpoke(grains, dly + 1 - r, row, 0);\n\t\tpoke(grains, age + 1, row, 1);\n\t}\n\tif (v == 0) {\n\t\tv1 = vout;\n\t}\n\telse {\n\t\tv2 = vout;\n\t}\n}\nwi = wrap(wi + 1, 0, ringsize);\n\ndrygain = 0;\nwet = v1;\nif (kind == 0) {\n\t// Fade to the dry signal as the shift reaches zero, so heel down has\n\t// no grain artifacts or latency\n\tz = clamp(abs(st) / 0.25, 0, 1);\n\tdrygain = 1 - z;\n\twet = v1 * z;\n}\nelse if (kind == 1) {\n\tdrygain = 0.707;\n\twet = v1 * 0.707;\n}\nelse {\n\tdrygain = 0.7;\n\twet = (v1 + v2) * 0.35;\n}\n\ndrygain = mix(1, drygain, onsm);\nwet = wet * onsm;\n\nout1 = in1 * drygain + wet;\nout2 = in2 * drygain + wet;\n",
									"fontface": 0,
									"fontname": "<Monospaced>",
									"fontsize": 12
								}
							},
							{
								"box": {
									"id": "out-1",
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										20,
										580,
										45,
										22
									],
									"text": "out 1"
								}
							},
							{
								"box": {
									"id": "out-2",
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										140,
										580,
										45,
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
										"in-1",
										0
									],
									"destination": [
										"code",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"in-2",
										0
									],
									"destination": [
										"code",
										1
									]
								}
							},
							{
								"patchline": {
									"source": [
										"code",
										0
									],
									"destination": [
										"out-1",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"code",
										1
									],
									"destination": [
										"out-2",
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
					"id": "obj-3",
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
					"id": "obj-4",
					"maxclass": "live.menu",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						200,
						20,
						100,
						15
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"presentation": 1,
					"presentation_rect": [
						8,
						24,
						100,
						15
					],
					"varname": "Mode",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Mode",
							"parameter_shortname": "Mode",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1
							],
							"parameter_mmin": 0,
							"parameter_mmax": 20,
							"parameter_enum": [
								"2 Oct Up",
								"Oct Up",
								"5th Up",
								"4th Up",
								"2nd Down",
								"4th Down",
								"5th Down",
								"Oct Down",
								"2 Oct Down",
								"Dive Bomb",
								"Deep Detune",
								"Shallow Detune",
								"Oct Dn/Oct Up",
								"5th Dn/4th Dn",
								"4th Dn/3rd Dn",
								"5th Up/7th Up",
								"5th Up/6th Up",
								"4th Up/5th Up",
								"3rd Up/4th Up",
								"b3rd Up/3rd Up",
								"2nd Up/3rd Up"
							]
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-5",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						200,
						60,
						90,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend mode"
				}
			},
			{
				"box": {
					"id": "obj-6",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						320,
						20,
						44,
						48
					],
					"outlettype": [
						"",
						"float"
					],
					"presentation": 1,
					"presentation_rect": [
						116,
						8,
						44,
						48
					],
					"varname": "Treadle",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Treadle",
							"parameter_shortname": "Treadle",
							"parameter_type": 0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0
							],
							"parameter_mmin": 0,
							"parameter_mmax": 127
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-7",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						320,
						80,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend treadle"
				}
			},
			{
				"box": {
					"id": "obj-8",
					"maxclass": "live.toggle",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						440,
						20,
						15,
						15
					],
					"outlettype": [
						""
					],
					"presentation": 1,
					"presentation_rect": [
						8,
						48,
						15,
						15
					],
					"varname": "Active",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Active",
							"parameter_shortname": "Active",
							"parameter_type": 2,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								1
							],
							"parameter_enum": [
								"off",
								"on"
							]
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-9",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						440,
						60,
						70,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend on"
				}
			},
			{
				"box": {
					"id": "obj-10",
					"maxclass": "comment",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						200,
						0,
						60,
						18
					],
					"text": "Mode",
					"presentation": 1,
					"presentation_rect": [
						8,
						6,
						60,
						18
					]
				}
			},
			{
				"box": {
					"id": "obj-11",
					"maxclass": "comment",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						460,
						18,
						50,
						18
					],
					"text": "Active",
					"presentation": 1,
					"presentation_rect": [
						26,
						46,
						50,
						18
					]
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
						"obj-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-1",
						1
					],
					"destination": [
						"obj-2",
						1
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
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-2",
						1
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
						"obj-4",
						0
					],
					"destination": [
						"obj-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-5",
						0
					],
					"destination": [
						"obj-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-6",
						0
					],
					"destination": [
						"obj-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-7",
						0
					],
					"destination": [
						"obj-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-8",
						0
					],
					"destination": [
						"obj-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-9",
						0
					],
					"destination": [
						"obj-2",
						0
					]
				}
			}
		]
	}
}