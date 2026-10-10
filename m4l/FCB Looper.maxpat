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
			1000,
			500
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
					"numoutlets": 1,
					"patching_rect": [
						200,
						20,
						140,
						22
					],
					"outlettype": [
						"signal"
					],
					"text": "phasor~ 1n @lock 1"
				}
			},
			{
				"box": {
					"id": "obj-3",
					"maxclass": "newobj",
					"numinlets": 3,
					"numoutlets": 5,
					"patching_rect": [
						20,
						200,
						300,
						22
					],
					"outlettype": [
						"signal",
						"signal",
						"signal",
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
									"id": "in-3",
									"maxclass": "newobj",
									"numinlets": 0,
									"numoutlets": 1,
									"patching_rect": [
										260,
										20,
										40,
										22
									],
									"outlettype": [
										""
									],
									"text": "in 3"
								}
							},
							{
								"box": {
									"id": "code",
									"maxclass": "codebox",
									"numinlets": 3,
									"numoutlets": 5,
									"patching_rect": [
										20,
										60,
										600,
										500
									],
									"outlettype": [
										"",
										"",
										"",
										"",
										""
									],
									"code": "// FCB Looper: three Boomerang style loops with their own clock.\n//\n// in1, in2: audio in (left, right)\n// in3: a phasor~ that goes from 0 to 1 once per bar of the song. Only\n//      used when sync_on is 1.\n// out1, out2: the loops (left, right). The dry input isn't passed through.\n// out3, out4, out5: status of loops 1-3\n//\n// Loops are controlled by setting tgt1, tgt2 and tgt3 to:\n//   0 stop, 1 record, 2 play, 3 overdub, 4 erase, 5 nothing\n// A loop reacts when its target changes, so setting 5 then the target\n// again repeats a command.\n//\n// Status is: 0 empty, 1 stopped, 2 recording, 3 playing, 4 overdubbing,\n//            5 waiting to start recording\n//\n// With sync_on 0, the first loop recorded sets the master length. The\n// other loops start recording, and start playing, when the master comes\n// around to its start, and stop recording on a multiple of its length.\n// Erasing every loop clears the master length.\n//\n// With sync_on 1, loops start, stop and finish recording on the next bar.\n// If autostop_bars is above 0, recording finishes after that many bars.\n\nParam tgt1(0);\nParam tgt2(0);\nParam tgt3(0);\nParam sync_on(0);\nParam autostop_bars(0);\nParam feedback(1);\n\nBuffer b1(\"fcbloop1\");\nBuffer b2(\"fcbloop2\");\nBuffer b3(\"fcbloop3\");\n\n// One row per loop:\n// 0 state, 1 pending, 2 position, 3 length, 4 bars recorded,\n// 5 last target, 6 overdub when it starts playing, 7 recording the master\nData loops(3, 8);\n\nHistory prevbar(0);\nHistory master(0);\nHistory clk(0);\n// 1 if the master length was set in the last sample\nHistory newmaster(0);\n\n// pending: 0 none, 1 start recording, 2 finish recording, 3 start playing, 4 stop\n\nmaxlen = dim(b1) - 1;\nbarwrap = in3 < prevbar - 0.5;\nprevbar = in3;\n\n// Loops before the master loop missed its start in the last sample, so\n// give them a boundary now. One sample late isn't audible.\nclkwrap = newmaster;\nnewmaster = 0;\nif (master > 0) {\n\tclk = clk + 1;\n\tif (clk >= master) {\n\t\tclk = 0;\n\t\tclkwrap = 1;\n\t}\n}\n\nmasterrec = 0;\nfor (i = 0; i < 3; i += 1) {\n\tif (peek(loops, i, 7) == 1 && peek(loops, i, 0) == 2) {\n\t\tmasterrec = 1;\n\t}\n}\n\noutl = 0;\noutr = 0;\nstatus1 = 0;\nstatus2 = 0;\nstatus3 = 0;\n\nfor (i = 0; i < 3; i += 1) {\n\tst = peek(loops, i, 0);\n\tpend = peek(loops, i, 1);\n\tpos = peek(loops, i, 2);\n\tlen = peek(loops, i, 3);\n\tbars = peek(loops, i, 4);\n\tlast = peek(loops, i, 5);\n\todafter = peek(loops, i, 6);\n\tismaster = peek(loops, i, 7);\n\n\tt = tgt3;\n\tif (i == 0) {\n\t\tt = tgt1;\n\t} else if (i == 1) {\n\t\tt = tgt2;\n\t}\n\tfree = sync_on == 0 && master == 0;\n\tfinish = 0;\n\n\t// Commands\n\tif (t != last) {\n\t\tlast = t;\n\t\tif (t == 4) {\n\t\t\tst = 0;\n\t\t\tpend = 0;\n\t\t\tpos = 0;\n\t\t\tlen = 0;\n\t\t\todafter = 0;\n\t\t\tismaster = 0;\n\t\t} else if (t == 1) {\n\t\t\tif (st == 0) {\n\t\t\t\tif (free && masterrec == 0) {\n\t\t\t\t\tst = 2;\n\t\t\t\t\tpend = 0;\n\t\t\t\t\tpos = 0;\n\t\t\t\t\tbars = 0;\n\t\t\t\t\todafter = 0;\n\t\t\t\t\tismaster = 1;\n\t\t\t\t\tmasterrec = 1;\n\t\t\t\t} else {\n\t\t\t\t\tpend = 1;\n\t\t\t\t}\n\t\t\t}\n\t\t} else if (t == 2 || t == 3) {\n\t\t\tif (st == 2) {\n\t\t\t\todafter = t == 3;\n\t\t\t\tif (ismaster == 1 && sync_on == 0) {\n\t\t\t\t\tfinish = 1;\n\t\t\t\t} else {\n\t\t\t\t\tpend = 2;\n\t\t\t\t}\n\t\t\t} else if (st == 0) {\n\t\t\t\t// Cancel waiting to record\n\t\t\t\tpend = 0;\n\t\t\t} else if (st == 1) {\n\t\t\t\todafter = t == 3;\n\t\t\t\tif (free) {\n\t\t\t\t\tst = 3 + odafter;\n\t\t\t\t\tpos = 0;\n\t\t\t\t} else {\n\t\t\t\t\tpend = 3;\n\t\t\t\t}\n\t\t\t} else if (st == 3 && t == 3) {\n\t\t\t\tst = 4;\n\t\t\t\tpend = 0;\n\t\t\t} else if (st == 4 && t == 2) {\n\t\t\t\tst = 3;\n\t\t\t\tpend = 0;\n\t\t\t} else {\n\t\t\t\t// Cancel a pending stop\n\t\t\t\tpend = 0;\n\t\t\t}\n\t\t} else if (t == 0) {\n\t\t\tif (st == 0 || st == 1) {\n\t\t\t\t// Cancel waiting to record or play\n\t\t\t\tpend = 0;\n\t\t\t} else if (st == 3 || st == 4) {\n\t\t\t\tif (sync_on == 1) {\n\t\t\t\t\tpend = 4;\n\t\t\t\t} else {\n\t\t\t\t\tst = 1;\n\t\t\t\t\tpend = 0;\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n\n\t// Timing\n\tboundary = clkwrap;\n\tif (sync_on == 1) {\n\t\tboundary = barwrap;\n\t}\n\tif (st == 2 && pos >= maxlen) {\n\t\t// Out of room\n\t\tfinish = 1;\n\t} else if (pend == 1 && free && masterrec == 0) {\n\t\t// Waiting for a master that was erased, so become the master\n\t\tst = 2;\n\t\tpend = 0;\n\t\tpos = 0;\n\t\tbars = 0;\n\t\todafter = 0;\n\t\tismaster = 1;\n\t\tmasterrec = 1;\n\t} else if (finish == 0 && boundary == 1) {\n\t\tif (st == 2 && ismaster == 0) {\n\t\t\tbars = bars + 1;\n\t\t\tif (pend == 2 || (sync_on == 1 && autostop_bars > 0 && bars >= autostop_bars)) {\n\t\t\t\tfinish = 1;\n\t\t\t}\n\t\t} else if (pend == 1) {\n\t\t\tst = 2;\n\t\t\tpend = 0;\n\t\t\tpos = 0;\n\t\t\tbars = 0;\n\t\t\todafter = 0;\n\t\t} else if (pend == 3) {\n\t\t\tst = 3 + odafter;\n\t\t\tpend = 0;\n\t\t\tpos = 0;\n\t\t} else if (pend == 4) {\n\t\t\tst = 1;\n\t\t\tpend = 0;\n\t\t}\n\t}\n\tif (finish == 1) {\n\t\tlen = pos;\n\t\tst = 3 + odafter;\n\t\tpend = 0;\n\t\tpos = 0;\n\t\tif (ismaster == 1) {\n\t\t\tismaster = 0;\n\t\t\tmasterrec = 0;\n\t\t\tif (master == 0 && len > 0) {\n\t\t\t\t// Loops after this one in the same sample see the new master start\n\t\t\t\tmaster = len;\n\t\t\t\tclk = 0;\n\t\t\t\tclkwrap = 1;\n\t\t\t\tnewmaster = i > 0;\n\t\t\t}\n\t\t}\n\t\tif (len == 0) {\n\t\t\tst = 0;\n\t\t}\n\t}\n\n\t// Audio\n\tl = 0;\n\tr = 0;\n\tif (st == 3 || st == 4) {\n\t\tif (i == 0) {\n\t\t\tl = peek(b1, pos, 0);\n\t\t\tr = peek(b1, pos, 1);\n\t\t} else if (i == 1) {\n\t\t\tl = peek(b2, pos, 0);\n\t\t\tr = peek(b2, pos, 1);\n\t\t} else {\n\t\t\tl = peek(b3, pos, 0);\n\t\t\tr = peek(b3, pos, 1);\n\t\t}\n\t\toutl = outl + l;\n\t\toutr = outr + r;\n\t}\n\tif (st == 2 || st == 4) {\n\t\twl = in1;\n\t\twr = in2;\n\t\tif (st == 4) {\n\t\t\twl = l * feedback + in1;\n\t\t\twr = r * feedback + in2;\n\t\t}\n\t\tif (i == 0) {\n\t\t\tpoke(b1, wl, pos, 0);\n\t\t\tpoke(b1, wr, pos, 1);\n\t\t} else if (i == 1) {\n\t\t\tpoke(b2, wl, pos, 0);\n\t\t\tpoke(b2, wr, pos, 1);\n\t\t} else {\n\t\t\tpoke(b3, wl, pos, 0);\n\t\t\tpoke(b3, wr, pos, 1);\n\t\t}\n\t}\n\tif (st >= 2) {\n\t\tpos = pos + 1;\n\t\tif (st != 2 && pos >= len) {\n\t\t\tpos = 0;\n\t\t}\n\t}\n\n\tstatus = st;\n\tif (st == 0 && pend == 1) {\n\t\tstatus = 5;\n\t}\n\tif (i == 0) {\n\t\tstatus1 = status;\n\t} else if (i == 1) {\n\t\tstatus2 = status;\n\t} else {\n\t\tstatus3 = status;\n\t}\n\n\tpoke(loops, st, i, 0);\n\tpoke(loops, pend, i, 1);\n\tpoke(loops, pos, i, 2);\n\tpoke(loops, len, i, 3);\n\tpoke(loops, bars, i, 4);\n\tpoke(loops, last, i, 5);\n\tpoke(loops, odafter, i, 6);\n\tpoke(loops, ismaster, i, 7);\n}\n\n// Erasing every loop clears the master length\nif (peek(loops, 0, 0) == 0 && peek(loops, 1, 0) == 0 && peek(loops, 2, 0) == 0 && masterrec == 0) {\n\tmaster = 0;\n\tclk = 0;\n}\n\nout1 = outl;\nout2 = outr;\nout3 = status1;\nout4 = status2;\nout5 = status3;\n",
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
							},
							{
								"box": {
									"id": "out-3",
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										260,
										580,
										45,
										22
									],
									"text": "out 3"
								}
							},
							{
								"box": {
									"id": "out-4",
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										380,
										580,
										45,
										22
									],
									"text": "out 4"
								}
							},
							{
								"box": {
									"id": "out-5",
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										500,
										580,
										45,
										22
									],
									"text": "out 5"
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
										"in-3",
										0
									],
									"destination": [
										"code",
										2
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
							},
							{
								"patchline": {
									"source": [
										"code",
										2
									],
									"destination": [
										"out-3",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"code",
										3
									],
									"destination": [
										"out-4",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"code",
										4
									],
									"destination": [
										"out-5",
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
					"id": "obj-4",
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
					"id": "obj-5",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						380,
						20,
						44,
						15
					],
					"outlettype": [
						"",
						"float"
					],
					"presentation": 1,
					"presentation_rect": [
						10,
						10,
						44,
						15
					],
					"varname": "target1",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "target1",
							"parameter_shortname": "target1",
							"parameter_type": 1,
							"parameter_mmin": 0,
							"parameter_mmax": 5
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-6",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						380,
						60,
						90,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend tgt1"
				}
			},
			{
				"box": {
					"id": "obj-7",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						490,
						20,
						44,
						15
					],
					"outlettype": [
						"",
						"float"
					],
					"presentation": 1,
					"presentation_rect": [
						60,
						10,
						44,
						15
					],
					"varname": "target2",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "target2",
							"parameter_shortname": "target2",
							"parameter_type": 1,
							"parameter_mmin": 0,
							"parameter_mmax": 5
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-8",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						490,
						60,
						90,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend tgt2"
				}
			},
			{
				"box": {
					"id": "obj-9",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						600,
						20,
						44,
						15
					],
					"outlettype": [
						"",
						"float"
					],
					"presentation": 1,
					"presentation_rect": [
						110,
						10,
						44,
						15
					],
					"varname": "target3",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "target3",
							"parameter_shortname": "target3",
							"parameter_type": 1,
							"parameter_mmin": 0,
							"parameter_mmax": 5
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-10",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						600,
						60,
						90,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend tgt3"
				}
			},
			{
				"box": {
					"id": "obj-11",
					"maxclass": "live.toggle",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						710,
						20,
						15,
						15
					],
					"outlettype": [
						""
					],
					"presentation": 1,
					"presentation_rect": [
						10,
						40,
						15,
						15
					],
					"varname": "sync",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "sync",
							"parameter_shortname": "sync",
							"parameter_type": 2,
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
					"id": "obj-12",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						710,
						60,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend sync_on"
				}
			},
			{
				"box": {
					"id": "obj-13",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						830,
						20,
						44,
						15
					],
					"outlettype": [
						"",
						"float"
					],
					"presentation": 1,
					"presentation_rect": [
						60,
						40,
						44,
						15
					],
					"varname": "autostop",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "autostop",
							"parameter_shortname": "autostop",
							"parameter_type": 1,
							"parameter_mmin": 0,
							"parameter_mmax": 8
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-14",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						830,
						60,
						130,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend autostop_bars"
				}
			},
			{
				"box": {
					"id": "obj-15",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						20,
						320,
						80,
						22
					],
					"outlettype": [
						"float"
					],
					"text": "snapshot~ 10"
				}
			},
			{
				"box": {
					"id": "obj-16",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						20,
						360,
						50,
						22
					],
					"outlettype": [
						"",
						"int",
						"int"
					],
					"text": "change"
				}
			},
			{
				"box": {
					"id": "obj-17",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						20,
						400,
						44,
						15
					],
					"outlettype": [
						"",
						"float"
					],
					"presentation": 1,
					"presentation_rect": [
						10,
						70,
						44,
						15
					],
					"varname": "status1",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "status1",
							"parameter_shortname": "status1",
							"parameter_type": 1,
							"parameter_mmin": 0,
							"parameter_mmax": 5
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-18",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						130,
						320,
						80,
						22
					],
					"outlettype": [
						"float"
					],
					"text": "snapshot~ 10"
				}
			},
			{
				"box": {
					"id": "obj-19",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						130,
						360,
						50,
						22
					],
					"outlettype": [
						"",
						"int",
						"int"
					],
					"text": "change"
				}
			},
			{
				"box": {
					"id": "obj-20",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						130,
						400,
						44,
						15
					],
					"outlettype": [
						"",
						"float"
					],
					"presentation": 1,
					"presentation_rect": [
						60,
						70,
						44,
						15
					],
					"varname": "status2",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "status2",
							"parameter_shortname": "status2",
							"parameter_type": 1,
							"parameter_mmin": 0,
							"parameter_mmax": 5
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-21",
					"maxclass": "newobj",
					"numinlets": 2,
					"numoutlets": 1,
					"patching_rect": [
						240,
						320,
						80,
						22
					],
					"outlettype": [
						"float"
					],
					"text": "snapshot~ 10"
				}
			},
			{
				"box": {
					"id": "obj-22",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						240,
						360,
						50,
						22
					],
					"outlettype": [
						"",
						"int",
						"int"
					],
					"text": "change"
				}
			},
			{
				"box": {
					"id": "obj-23",
					"maxclass": "live.numbox",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						240,
						400,
						44,
						15
					],
					"outlettype": [
						"",
						"float"
					],
					"presentation": 1,
					"presentation_rect": [
						110,
						70,
						44,
						15
					],
					"varname": "status3",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "status3",
							"parameter_shortname": "status3",
							"parameter_type": 1,
							"parameter_mmin": 0,
							"parameter_mmax": 5
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-24",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						380,
						320,
						150,
						22
					],
					"outlettype": [
						"float",
						"bang"
					],
					"text": "buffer~ fcbloop1 60000 2"
				}
			},
			{
				"box": {
					"id": "obj-25",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						540,
						320,
						150,
						22
					],
					"outlettype": [
						"float",
						"bang"
					],
					"text": "buffer~ fcbloop2 60000 2"
				}
			},
			{
				"box": {
					"id": "obj-26",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						700,
						320,
						150,
						22
					],
					"outlettype": [
						"float",
						"bang"
					],
					"text": "buffer~ fcbloop3 60000 2"
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
						"obj-1",
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
						"obj-2",
						0
					],
					"destination": [
						"obj-3",
						2
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
						"obj-4",
						1
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
						"obj-6",
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
						"obj-3",
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
						"obj-8",
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
						"obj-3",
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
						"obj-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-10",
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
						"obj-11",
						0
					],
					"destination": [
						"obj-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-12",
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
						"obj-13",
						0
					],
					"destination": [
						"obj-14",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-14",
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
						"obj-3",
						2
					],
					"destination": [
						"obj-15",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-15",
						0
					],
					"destination": [
						"obj-16",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-16",
						0
					],
					"destination": [
						"obj-17",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						3
					],
					"destination": [
						"obj-18",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-18",
						0
					],
					"destination": [
						"obj-19",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-19",
						0
					],
					"destination": [
						"obj-20",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						4
					],
					"destination": [
						"obj-21",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-21",
						0
					],
					"destination": [
						"obj-22",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-22",
						0
					],
					"destination": [
						"obj-23",
						0
					]
				}
			}
		]
	}
}