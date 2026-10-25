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
		"devicewidth": 312.0,
		"description": "King of Tone style dual overdrive",
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
					"text": "gen~ @title kingtone",
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
									"code": "// Kingtone: an Analogman King of Tone style dual overdrive for gen~.\n// Signal levels are treated as volts: 1.0 (0 dBFS) = 1 V peak.\n// Keep this file in step with reference.py, which mirrors it for testing.\n//\n// This is a template, expanded by build.py in two passes:\n//  1. Each block between SIDE markers is copied once per side, replacing\n//     $ with the side's letter (a feeds b, like the pedal's two sides in\n//     series).\n//  2. Everything between the CHANNEL markers, and every other line\n//     containing @, is copied once per channel, replacing @ with the\n//     channel number.\n// The code uses no user functions, so every filter's state is an explicit\n// History, and all declarations come before any statement.\n\nParam a_on(1, min=0, max=1);\nParam a_mode(1, min=0, max=2);\nParam a_drive(5, min=0, max=10);\nParam a_tone(5, min=0, max=10);\nParam a_volume(5, min=0, max=10);\nParam a_presence(5, min=0, max=10);\nHistory s_aon(0);\nHistory s_adrive(0.5);\nHistory s_atone(-5.5);\nHistory s_apres(4.5);\nHistory s_avol(1);\nHistory s_awb(0);\nHistory s_awo(1);\nHistory s_awd(0);\nHistory z_ain1(0);\nHistory z_ain2(0);\nHistory z_ahp1(0);\nHistory z_ahp2(0);\nHistory z_apre1(0);\nHistory z_apre2(0);\nHistory z_atone1(0);\nHistory z_atone2(0);\nHistory z_apres1(0);\nHistory z_apres2(0);\nHistory z_aout1(0);\nHistory z_aout2(0);\nHistory u_aod1(0);\nHistory u_aod2(0);\nHistory u_ads1(0);\nHistory u_ads2(0);\nParam b_on(1, min=0, max=1);\nParam b_mode(1, min=0, max=2);\nParam b_drive(5, min=0, max=10);\nParam b_tone(5, min=0, max=10);\nParam b_volume(5, min=0, max=10);\nParam b_presence(5, min=0, max=10);\nHistory s_bon(0);\nHistory s_bdrive(0.5);\nHistory s_btone(-5.5);\nHistory s_bpres(4.5);\nHistory s_bvol(1);\nHistory s_bwb(0);\nHistory s_bwo(1);\nHistory s_bwd(0);\nHistory z_bin1(0);\nHistory z_bin2(0);\nHistory z_bhp1(0);\nHistory z_bhp2(0);\nHistory z_bpre1(0);\nHistory z_bpre2(0);\nHistory z_btone1(0);\nHistory z_btone2(0);\nHistory z_bpres1(0);\nHistory z_bpres2(0);\nHistory z_bout1(0);\nHistory z_bout2(0);\nHistory u_bod1(0);\nHistory u_bod2(0);\nHistory u_bds1(0);\nHistory u_bds2(0);\n\n// 20 ms parameter smoothing.\nk = 1 - exp(-1 / (0.02 * samplerate));\n\n// One-pole TPT lowpass coefficients, G = g / (1 + g) with g = tan(pi fc / sr).\n// Each filter below is: v = (x - z) * G; y = v + z; z = y + v.\n// Input coupling cap (10 nF into 1 M): 16 Hz.\ng = tan(pi * 16 / samplerate);\nc_in = g / (1 + g);\n// Drive stage ground leg (4.7 k + 100 nF): gain only applies above 340 Hz.\ng = tan(pi * 340 / samplerate);\nc_hp = g / (1 + g);\n// Tone shelf and presence shelf corners.\ng = tan(pi * 1000 / samplerate);\nc_tone = g / (1 + g);\ng = tan(pi * 3200 / samplerate);\nc_pres = g / (1 + g);\n// Output coupling cap.\ng = tan(pi * 8 / samplerate);\nc_out = g / (1 + g);\n\ns_aon = s_aon + ((a_on > 0.5) - s_aon) * k;\ns_adrive = s_adrive + (a_drive / 10 - s_adrive) * k;\ns_atone = s_atone + ((-14 + 1.7 * a_tone) - s_atone) * k;\ns_apres = s_apres + (0.9 * a_presence - s_apres) * k;\n// Volume: audio-taper pot, about unity at noon with Drive at 0.\ns_avol = s_avol + (6.5 * (pow(30, a_volume / 10) - 1) / 29 - s_avol) * k;\n// Mode switch (0 Boost, 1 Overdrive, 2 Distortion), crossfaded.\ns_awb = s_awb + ((a_mode < 0.5) - s_awb) * k;\ns_awo = s_awo + ((a_mode > 0.5) * (a_mode < 1.5) - s_awo) * k;\ns_awd = s_awd + ((a_mode > 1.5) - s_awd) * k;\n\n// Drive pot (100 k audio taper) plus 1 k in the feedback leg, over 4.7 k\n// to ground: the stage gain above 340 Hz is 1 + rf / 4.7 k.\nrf_a = 1000 + 100000 * (pow(30, s_adrive) - 1) / 29;\ngm1_a = rf_a / 4700;\n// The feedback cap (about 220 pF) across rf rolls the top end off as\n// Drive goes up: about 19 kHz at minimum, 5 kHz at maximum.\ng = tan(pi * 20000 / (1 + rf_a / 36000) / samplerate);\nc_apre = g / (1 + g);\ntone_amp_a = dbtoa(s_atone);\npres_amp_a = dbtoa(s_apres);\ns_bon = s_bon + ((b_on > 0.5) - s_bon) * k;\ns_bdrive = s_bdrive + (b_drive / 10 - s_bdrive) * k;\ns_btone = s_btone + ((-14 + 1.7 * b_tone) - s_btone) * k;\ns_bpres = s_bpres + (0.9 * b_presence - s_bpres) * k;\n// Volume: audio-taper pot, about unity at noon with Drive at 0.\ns_bvol = s_bvol + (6.5 * (pow(30, b_volume / 10) - 1) / 29 - s_bvol) * k;\n// Mode switch (0 Boost, 1 Overdrive, 2 Distortion), crossfaded.\ns_bwb = s_bwb + ((b_mode < 0.5) - s_bwb) * k;\ns_bwo = s_bwo + ((b_mode > 0.5) * (b_mode < 1.5) - s_bwo) * k;\ns_bwd = s_bwd + ((b_mode > 1.5) - s_bwd) * k;\n\n// Drive pot (100 k audio taper) plus 1 k in the feedback leg, over 4.7 k\n// to ground: the stage gain above 340 Hz is 1 + rf / 4.7 k.\nrf_b = 1000 + 100000 * (pow(30, s_bdrive) - 1) / 29;\ngm1_b = rf_b / 4700;\n// The feedback cap (about 220 pF) across rf rolls the top end off as\n// Drive goes up: about 19 kHz at minimum, 5 kHz at maximum.\ng = tan(pi * 20000 / (1 + rf_b / 36000) / samplerate);\nc_bpre = g / (1 + g);\ntone_amp_b = dbtoa(s_btone);\npres_amp_b = dbtoa(s_bpres);\n\n// Channel 1\nsig1 = in1;\n\ndry = sig1;\n\n// Input coupling cap.\nv = (dry - z_ain1) * c_in;\nlp = v + z_ain1;\nz_ain1 = lp + v;\nx = dry - lp;\n\n// Current through the feedback leg: the input above the ground-leg corner,\n// times rf / 4.7 k, then lowpassed by the feedback cap.\nv = (x - z_ahp1) * c_hp;\nlp = v + z_ahp1;\nz_ahp1 = lp + v;\nfb = gm1_a * (x - lp);\nv = (fb - z_apre1) * c_apre;\nlp = v + z_apre1;\nz_apre1 = lp + v;\nfb = lp;\n\n// Overdrive: silicon diodes across the feedback leg. They cap the voltage\n// across the feedback leg at about 0.55 V, but the non-inverting stage\n// still adds the input on top (out = in + v_feedback), so the dry signal\n// always comes through. x / sqrt(1 + x^2) with first-order antiderivative\n// anti-aliasing: (F(u) - F(u1)) / (u - u1) = (u + u1) / (F(u) + F(u1)).\nu = fb / 0.55;\nod = x + 0.55 * (u + u_aod1) / (sqrt(1 + u * u) + sqrt(1 + u_aod1 * u_aod1));\nu_aod1 = u;\n\n// Distortion: the diodes move to ground after the stage, so the op-amp\n// runs at full gain and everything, dry signal included, is clipped at\n// about 0.5 V.\nu = (x + fb) / 0.5;\nds = 0.5 * (u + u_ads1) / (sqrt(1 + u * u) + sqrt(1 + u_ads1 * u_ads1));\nu_ads1 = u;\n\n// Boost: no diodes; only the 9 V op-amp rails (about 3.8 V) limit it.\nu = (x + fb) / 3.8;\nbs = 3.8 * u / sqrt(1 + u * u);\n\ny = s_awb * bs + s_awo * od + s_awd * ds;\n\n// Tone: treble shelf around 1 kHz, -14 dB fully down to +3 dB fully up.\nv = (y - z_atone1) * c_tone;\nlp = v + z_atone1;\nz_atone1 = lp + v;\ny = lp + tone_amp_a * (y - lp);\n\n// Presence (an internal trimmer on the pedal): 0 to +9 dB above 3.2 kHz.\nv = (y - z_apres1) * c_pres;\nlp = v + z_apres1;\nz_apres1 = lp + v;\ny = (lp + pres_amp_a * (y - lp)) * s_avol;\n\n// Output coupling cap.\nv = (y - z_aout1) * c_out;\nlp = v + z_aout1;\nz_aout1 = lp + v;\ny = y - lp;\n\n// True bypass footswitch, crossfaded to avoid clicks.\nsig1 = dry + s_aon * (y - dry);\ndry = sig1;\n\n// Input coupling cap.\nv = (dry - z_bin1) * c_in;\nlp = v + z_bin1;\nz_bin1 = lp + v;\nx = dry - lp;\n\n// Current through the feedback leg: the input above the ground-leg corner,\n// times rf / 4.7 k, then lowpassed by the feedback cap.\nv = (x - z_bhp1) * c_hp;\nlp = v + z_bhp1;\nz_bhp1 = lp + v;\nfb = gm1_b * (x - lp);\nv = (fb - z_bpre1) * c_bpre;\nlp = v + z_bpre1;\nz_bpre1 = lp + v;\nfb = lp;\n\n// Overdrive: silicon diodes across the feedback leg. They cap the voltage\n// across the feedback leg at about 0.55 V, but the non-inverting stage\n// still adds the input on top (out = in + v_feedback), so the dry signal\n// always comes through. x / sqrt(1 + x^2) with first-order antiderivative\n// anti-aliasing: (F(u) - F(u1)) / (u - u1) = (u + u1) / (F(u) + F(u1)).\nu = fb / 0.55;\nod = x + 0.55 * (u + u_bod1) / (sqrt(1 + u * u) + sqrt(1 + u_bod1 * u_bod1));\nu_bod1 = u;\n\n// Distortion: the diodes move to ground after the stage, so the op-amp\n// runs at full gain and everything, dry signal included, is clipped at\n// about 0.5 V.\nu = (x + fb) / 0.5;\nds = 0.5 * (u + u_bds1) / (sqrt(1 + u * u) + sqrt(1 + u_bds1 * u_bds1));\nu_bds1 = u;\n\n// Boost: no diodes; only the 9 V op-amp rails (about 3.8 V) limit it.\nu = (x + fb) / 3.8;\nbs = 3.8 * u / sqrt(1 + u * u);\n\ny = s_bwb * bs + s_bwo * od + s_bwd * ds;\n\n// Tone: treble shelf around 1 kHz, -14 dB fully down to +3 dB fully up.\nv = (y - z_btone1) * c_tone;\nlp = v + z_btone1;\nz_btone1 = lp + v;\ny = lp + tone_amp_b * (y - lp);\n\n// Presence (an internal trimmer on the pedal): 0 to +9 dB above 3.2 kHz.\nv = (y - z_bpres1) * c_pres;\nlp = v + z_bpres1;\nz_bpres1 = lp + v;\ny = (lp + pres_amp_b * (y - lp)) * s_bvol;\n\n// Output coupling cap.\nv = (y - z_bout1) * c_out;\nlp = v + z_bout1;\nz_bout1 = lp + v;\ny = y - lp;\n\n// True bypass footswitch, crossfaded to avoid clicks.\nsig1 = dry + s_bon * (y - dry);\n\nout1 = sig1;\n\n// Channel 2\nsig2 = in2;\n\ndry = sig2;\n\n// Input coupling cap.\nv = (dry - z_ain2) * c_in;\nlp = v + z_ain2;\nz_ain2 = lp + v;\nx = dry - lp;\n\n// Current through the feedback leg: the input above the ground-leg corner,\n// times rf / 4.7 k, then lowpassed by the feedback cap.\nv = (x - z_ahp2) * c_hp;\nlp = v + z_ahp2;\nz_ahp2 = lp + v;\nfb = gm1_a * (x - lp);\nv = (fb - z_apre2) * c_apre;\nlp = v + z_apre2;\nz_apre2 = lp + v;\nfb = lp;\n\n// Overdrive: silicon diodes across the feedback leg. They cap the voltage\n// across the feedback leg at about 0.55 V, but the non-inverting stage\n// still adds the input on top (out = in + v_feedback), so the dry signal\n// always comes through. x / sqrt(1 + x^2) with first-order antiderivative\n// anti-aliasing: (F(u) - F(u1)) / (u - u1) = (u + u1) / (F(u) + F(u1)).\nu = fb / 0.55;\nod = x + 0.55 * (u + u_aod2) / (sqrt(1 + u * u) + sqrt(1 + u_aod2 * u_aod2));\nu_aod2 = u;\n\n// Distortion: the diodes move to ground after the stage, so the op-amp\n// runs at full gain and everything, dry signal included, is clipped at\n// about 0.5 V.\nu = (x + fb) / 0.5;\nds = 0.5 * (u + u_ads2) / (sqrt(1 + u * u) + sqrt(1 + u_ads2 * u_ads2));\nu_ads2 = u;\n\n// Boost: no diodes; only the 9 V op-amp rails (about 3.8 V) limit it.\nu = (x + fb) / 3.8;\nbs = 3.8 * u / sqrt(1 + u * u);\n\ny = s_awb * bs + s_awo * od + s_awd * ds;\n\n// Tone: treble shelf around 1 kHz, -14 dB fully down to +3 dB fully up.\nv = (y - z_atone2) * c_tone;\nlp = v + z_atone2;\nz_atone2 = lp + v;\ny = lp + tone_amp_a * (y - lp);\n\n// Presence (an internal trimmer on the pedal): 0 to +9 dB above 3.2 kHz.\nv = (y - z_apres2) * c_pres;\nlp = v + z_apres2;\nz_apres2 = lp + v;\ny = (lp + pres_amp_a * (y - lp)) * s_avol;\n\n// Output coupling cap.\nv = (y - z_aout2) * c_out;\nlp = v + z_aout2;\nz_aout2 = lp + v;\ny = y - lp;\n\n// True bypass footswitch, crossfaded to avoid clicks.\nsig2 = dry + s_aon * (y - dry);\ndry = sig2;\n\n// Input coupling cap.\nv = (dry - z_bin2) * c_in;\nlp = v + z_bin2;\nz_bin2 = lp + v;\nx = dry - lp;\n\n// Current through the feedback leg: the input above the ground-leg corner,\n// times rf / 4.7 k, then lowpassed by the feedback cap.\nv = (x - z_bhp2) * c_hp;\nlp = v + z_bhp2;\nz_bhp2 = lp + v;\nfb = gm1_b * (x - lp);\nv = (fb - z_bpre2) * c_bpre;\nlp = v + z_bpre2;\nz_bpre2 = lp + v;\nfb = lp;\n\n// Overdrive: silicon diodes across the feedback leg. They cap the voltage\n// across the feedback leg at about 0.55 V, but the non-inverting stage\n// still adds the input on top (out = in + v_feedback), so the dry signal\n// always comes through. x / sqrt(1 + x^2) with first-order antiderivative\n// anti-aliasing: (F(u) - F(u1)) / (u - u1) = (u + u1) / (F(u) + F(u1)).\nu = fb / 0.55;\nod = x + 0.55 * (u + u_bod2) / (sqrt(1 + u * u) + sqrt(1 + u_bod2 * u_bod2));\nu_bod2 = u;\n\n// Distortion: the diodes move to ground after the stage, so the op-amp\n// runs at full gain and everything, dry signal included, is clipped at\n// about 0.5 V.\nu = (x + fb) / 0.5;\nds = 0.5 * (u + u_bds2) / (sqrt(1 + u * u) + sqrt(1 + u_bds2 * u_bds2));\nu_bds2 = u;\n\n// Boost: no diodes; only the 9 V op-amp rails (about 3.8 V) limit it.\nu = (x + fb) / 3.8;\nbs = 3.8 * u / sqrt(1 + u * u);\n\ny = s_bwb * bs + s_bwo * od + s_bwd * ds;\n\n// Tone: treble shelf around 1 kHz, -14 dB fully down to +3 dB fully up.\nv = (y - z_btone2) * c_tone;\nlp = v + z_btone2;\nz_btone2 = lp + v;\ny = lp + tone_amp_b * (y - lp);\n\n// Presence (an internal trimmer on the pedal): 0 to +9 dB above 3.2 kHz.\nv = (y - z_bpres2) * c_pres;\nlp = v + z_bpres2;\nz_bpres2 = lp + v;\ny = (lp + pres_amp_b * (y - lp)) * s_bvol;\n\n// Output coupling cap.\nv = (y - z_bout2) * c_out;\nlp = v + z_bout2;\nz_bout2 = lp + v;\ny = y - lp;\n\n// True bypass footswitch, crossfaded to avoid clicks.\nsig2 = dry + s_bon * (y - dry);\n\nout2 = sig2;\n",
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
					"text": "KINGTONE",
					"presentation": 1,
					"presentation_rect": [
						64,
						120,
						96,
						20
					],
					"fontsize": 11,
					"fontface": 1
				}
			},
			{
				"box": {
					"id": "obj-label-0",
					"maxclass": "comment",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						300,
						20,
						50,
						20
					],
					"text": "CH 1",
					"presentation": 1,
					"presentation_rect": [
						28,
						2,
						50,
						18
					],
					"fontsize": 11,
					"fontface": 1
				}
			},
			{
				"box": {
					"id": "obj-ctl-0",
					"maxclass": "live.toggle",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						160,
						60,
						16,
						16
					],
					"outlettype": [
						""
					],
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						8,
						4,
						16,
						16
					],
					"varname": "ch1_on",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 1 On",
							"parameter_shortname": "On",
							"parameter_type": 2,
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1,
							"parameter_initial": [
								1
							],
							"parameter_initial_enable": 1
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
					"text": "prepend a_on"
				}
			},
			{
				"box": {
					"id": "obj-ctl-1",
					"maxclass": "live.tab",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						270,
						60,
						140,
						18
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						8,
						22,
						140,
						18
					],
					"varname": "ch1_mode",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 1 Mode",
							"parameter_shortname": "Mode",
							"parameter_type": 2,
							"parameter_enum": [
								"Boost",
								"OD",
								"Dist"
							],
							"parameter_mmax": 2,
							"parameter_initial": [
								1
							],
							"parameter_initial_enable": 1,
							"parameter_unitstyle": 9
						}
					},
					"num_lines_patching": 1,
					"num_lines_presentation": 1
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
					"text": "prepend a_mode"
				}
			},
			{
				"box": {
					"id": "obj-ctl-2",
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
						8,
						44,
						44,
						48
					],
					"varname": "ch1_volume",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 1 Volume",
							"parameter_shortname": "Volume",
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
					"text": "prepend a_volume"
				}
			},
			{
				"box": {
					"id": "obj-ctl-3",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						490,
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
						56,
						44,
						44,
						48
					],
					"varname": "ch1_drive",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 1 Drive",
							"parameter_shortname": "Drive",
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
					"id": "obj-prepend-3",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						490,
						130,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend a_drive"
				}
			},
			{
				"box": {
					"id": "obj-ctl-4",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						600,
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
						104,
						44,
						44,
						48
					],
					"varname": "ch1_tone",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 1 Tone",
							"parameter_shortname": "Tone",
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
					"id": "obj-prepend-4",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						600,
						130,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend a_tone"
				}
			},
			{
				"box": {
					"id": "obj-ctl-5",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						710,
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
						100,
						44,
						48
					],
					"varname": "ch1_presence",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 1 Presence",
							"parameter_shortname": "Presence",
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
					"id": "obj-prepend-5",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						710,
						130,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend a_presence"
				}
			},
			{
				"box": {
					"id": "obj-label-1",
					"maxclass": "comment",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						360,
						20,
						50,
						20
					],
					"text": "CH 2",
					"presentation": 1,
					"presentation_rect": [
						184,
						2,
						50,
						18
					],
					"fontsize": 11,
					"fontface": 1
				}
			},
			{
				"box": {
					"id": "obj-ctl-6",
					"maxclass": "live.toggle",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						160,
						180,
						16,
						16
					],
					"outlettype": [
						""
					],
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						164,
						4,
						16,
						16
					],
					"varname": "ch2_on",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 2 On",
							"parameter_shortname": "On",
							"parameter_type": 2,
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1,
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
					"id": "obj-prepend-6",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						160,
						250,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend b_on"
				}
			},
			{
				"box": {
					"id": "obj-ctl-7",
					"maxclass": "live.tab",
					"numinlets": 1,
					"numoutlets": 3,
					"patching_rect": [
						270,
						180,
						140,
						18
					],
					"outlettype": [
						"",
						"",
						"float"
					],
					"parameter_enable": 1,
					"presentation": 1,
					"presentation_rect": [
						164,
						22,
						140,
						18
					],
					"varname": "ch2_mode",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 2 Mode",
							"parameter_shortname": "Mode",
							"parameter_type": 2,
							"parameter_enum": [
								"Boost",
								"OD",
								"Dist"
							],
							"parameter_mmax": 2,
							"parameter_initial": [
								1
							],
							"parameter_initial_enable": 1,
							"parameter_unitstyle": 9
						}
					},
					"num_lines_patching": 1,
					"num_lines_presentation": 1
				}
			},
			{
				"box": {
					"id": "obj-prepend-7",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						270,
						250,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend b_mode"
				}
			},
			{
				"box": {
					"id": "obj-ctl-8",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						380,
						180,
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
						164,
						44,
						44,
						48
					],
					"varname": "ch2_volume",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 2 Volume",
							"parameter_shortname": "Volume",
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
					"id": "obj-prepend-8",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						380,
						250,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend b_volume"
				}
			},
			{
				"box": {
					"id": "obj-ctl-9",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						490,
						180,
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
						212,
						44,
						44,
						48
					],
					"varname": "ch2_drive",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 2 Drive",
							"parameter_shortname": "Drive",
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
					"id": "obj-prepend-9",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						490,
						250,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend b_drive"
				}
			},
			{
				"box": {
					"id": "obj-ctl-10",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						600,
						180,
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
						260,
						44,
						44,
						48
					],
					"varname": "ch2_tone",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 2 Tone",
							"parameter_shortname": "Tone",
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
					"id": "obj-prepend-10",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						600,
						250,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend b_tone"
				}
			},
			{
				"box": {
					"id": "obj-ctl-11",
					"maxclass": "live.dial",
					"numinlets": 1,
					"numoutlets": 2,
					"patching_rect": [
						710,
						180,
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
						164,
						100,
						44,
						48
					],
					"varname": "ch2_presence",
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "CH 2 Presence",
							"parameter_shortname": "Presence",
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
					"id": "obj-prepend-11",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"patching_rect": [
						710,
						250,
						100,
						22
					],
					"outlettype": [
						""
					],
					"text": "prepend b_presence"
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
						"obj-ctl-0",
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
						"obj-ctl-1",
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
						"obj-ctl-2",
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
			},
			{
				"patchline": {
					"source": [
						"obj-ctl-3",
						0
					],
					"destination": [
						"obj-prepend-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-3",
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
						"obj-ctl-4",
						0
					],
					"destination": [
						"obj-prepend-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-4",
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
						"obj-ctl-5",
						0
					],
					"destination": [
						"obj-prepend-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-5",
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
						"obj-ctl-6",
						0
					],
					"destination": [
						"obj-prepend-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-6",
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
						"obj-ctl-7",
						0
					],
					"destination": [
						"obj-prepend-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-7",
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
						"obj-ctl-8",
						0
					],
					"destination": [
						"obj-prepend-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-8",
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
						"obj-ctl-9",
						0
					],
					"destination": [
						"obj-prepend-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-9",
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
						"obj-ctl-10",
						0
					],
					"destination": [
						"obj-prepend-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-10",
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
						"obj-ctl-11",
						0
					],
					"destination": [
						"obj-prepend-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-prepend-11",
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
			"obj-ctl-0": [
				"CH 1 On",
				"On",
				0
			],
			"obj-ctl-1": [
				"CH 1 Mode",
				"Mode",
				0
			],
			"obj-ctl-2": [
				"CH 1 Volume",
				"Volume",
				0
			],
			"obj-ctl-3": [
				"CH 1 Drive",
				"Drive",
				0
			],
			"obj-ctl-4": [
				"CH 1 Tone",
				"Tone",
				0
			],
			"obj-ctl-5": [
				"CH 1 Presence",
				"Presence",
				0
			],
			"obj-ctl-6": [
				"CH 2 On",
				"On",
				0
			],
			"obj-ctl-7": [
				"CH 2 Mode",
				"Mode",
				0
			],
			"obj-ctl-8": [
				"CH 2 Volume",
				"Volume",
				0
			],
			"obj-ctl-9": [
				"CH 2 Drive",
				"Drive",
				0
			],
			"obj-ctl-10": [
				"CH 2 Tone",
				"Tone",
				0
			],
			"obj-ctl-11": [
				"CH 2 Presence",
				"Presence",
				0
			],
			"parameterbanks": {
				"0": {
					"index": 0,
					"name": "CH 1",
					"parameters": [
						"CH 1 On",
						"CH 1 Mode",
						"CH 1 Volume",
						"CH 1 Drive",
						"CH 1 Tone",
						"CH 1 Presence",
						"-",
						"-"
					]
				},
				"1": {
					"index": 1,
					"name": "CH 2",
					"parameters": [
						"CH 2 On",
						"CH 2 Mode",
						"CH 2 Volume",
						"CH 2 Drive",
						"CH 2 Tone",
						"CH 2 Presence",
						"-",
						"-"
					]
				}
			},
			"inherited_shortname": 1
		},
		"dependency_cache": [],
		"latency": 0,
		"is_mpe": 0,
		"minimum_live_version": "",
		"minimum_max_version": "",
		"platform_compatibility": 0,
		"autosave": 0
	}
}
