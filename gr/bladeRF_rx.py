#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Simple bladeRF RX GUI
# Author: Nuand, LLC <bladeRF@nuand.com>
# Description: A simple RX-only GUI that demonstrates the usage of various RX controls.
# GNU Radio version: 3.10.10.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSlot
from gnuradio import analog
from gnuradio import audio
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
import osmosdr
import time
import sip



class bladeRF_rx(gr.top_block, Qt.QWidget):

    def __init__(self, buflen=4096, dc_offset_i=0, dc_offset_q=0, instance=0, num_buffers=16, num_xfers=8, rx_bandwidth=1.5e6, rx_frequency=96.9e6, rx_lna_gain=6, rx_sample_rate=1.92e6, rx_vga_gain=30, serial="", verbosity="info"):
        gr.top_block.__init__(self, "Simple bladeRF RX GUI", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Simple bladeRF RX GUI")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "bladeRF_rx")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)

        ##################################################
        # Parameters
        ##################################################
        self.buflen = buflen
        self.dc_offset_i = dc_offset_i
        self.dc_offset_q = dc_offset_q
        self.instance = instance
        self.num_buffers = num_buffers
        self.num_xfers = num_xfers
        self.rx_bandwidth = rx_bandwidth
        self.rx_frequency = rx_frequency
        self.rx_lna_gain = rx_lna_gain
        self.rx_sample_rate = rx_sample_rate
        self.rx_vga_gain = rx_vga_gain
        self.serial = serial
        self.verbosity = verbosity

        ##################################################
        # Variables
        ##################################################
        self.bladerf_selection = bladerf_selection = str(instance) if serial == "" else serial
        self.bladerf_args = bladerf_args = "bladerf=" + bladerf_selection + ",buffers=" + str(num_buffers) + ",buflen=" + str(buflen) + ",num_xfers=" + str(num_xfers) + ",verbosity="+verbosity
        self.gui_rx_vga_gain = gui_rx_vga_gain = rx_vga_gain
        self.gui_rx_sample_rate = gui_rx_sample_rate = rx_sample_rate
        self.gui_rx_lna_gain = gui_rx_lna_gain = rx_lna_gain
        self.gui_rx_frequency = gui_rx_frequency = rx_frequency
        self.gui_rx_bandwidth = gui_rx_bandwidth = rx_bandwidth
        self.gui_dc_offset_q = gui_dc_offset_q = dc_offset_q
        self.gui_dc_offset_i = gui_dc_offset_i = dc_offset_i
        self.gui_bladerf_args = gui_bladerf_args = bladerf_args

        ##################################################
        # Blocks
        ##################################################

        self._gui_rx_vga_gain_range = qtgui.Range(5, 60, 1, rx_vga_gain, 200)
        self._gui_rx_vga_gain_win = qtgui.RangeWidget(self._gui_rx_vga_gain_range, self.set_gui_rx_vga_gain, "RX VGA1 + VGA2 Gain", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._gui_rx_vga_gain_win, 0, 5, 1, 4)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(5, 9):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._gui_rx_sample_rate_range = qtgui.Range(1.5e6, 40e6, 500e3, rx_sample_rate, 200)
        self._gui_rx_sample_rate_win = qtgui.RangeWidget(self._gui_rx_sample_rate_range, self.set_gui_rx_sample_rate, "Sample Rate", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._gui_rx_sample_rate_win, 1, 0, 1, 2)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        # Create the options list
        self._gui_rx_lna_gain_options = [0, 3, 6]
        # Create the labels list
        self._gui_rx_lna_gain_labels = ['0 dB', '3 dB', '6 dB']
        # Create the combo box
        self._gui_rx_lna_gain_tool_bar = Qt.QToolBar(self)
        self._gui_rx_lna_gain_tool_bar.addWidget(Qt.QLabel("LNA Gain" + ": "))
        self._gui_rx_lna_gain_combo_box = Qt.QComboBox()
        self._gui_rx_lna_gain_tool_bar.addWidget(self._gui_rx_lna_gain_combo_box)
        for _label in self._gui_rx_lna_gain_labels: self._gui_rx_lna_gain_combo_box.addItem(_label)
        self._gui_rx_lna_gain_callback = lambda i: Qt.QMetaObject.invokeMethod(self._gui_rx_lna_gain_combo_box, "setCurrentIndex", Qt.Q_ARG("int", self._gui_rx_lna_gain_options.index(i)))
        self._gui_rx_lna_gain_callback(self.gui_rx_lna_gain)
        self._gui_rx_lna_gain_combo_box.currentIndexChanged.connect(
            lambda i: self.set_gui_rx_lna_gain(self._gui_rx_lna_gain_options[i]))
        # Create the radio buttons
        self.top_grid_layout.addWidget(self._gui_rx_lna_gain_tool_bar, 0, 9, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(9, 10):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._gui_rx_frequency_range = qtgui.Range(0, 3.8e9, 1e6, rx_frequency, 200)
        self._gui_rx_frequency_win = qtgui.RangeWidget(self._gui_rx_frequency_range, self.set_gui_rx_frequency, "Frequency", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._gui_rx_frequency_win, 0, 0, 1, 5)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 5):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._gui_rx_bandwidth_range = qtgui.Range(1.5e6, 28e6, 0.5e6, rx_bandwidth, 200)
        self._gui_rx_bandwidth_win = qtgui.RangeWidget(self._gui_rx_bandwidth_range, self.set_gui_rx_bandwidth, "Bandwidth", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._gui_rx_bandwidth_win, 1, 2, 1, 2)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._gui_dc_offset_q_range = qtgui.Range(-1.0, 1.0, (1.0 / 2048.0), dc_offset_q, 200)
        self._gui_dc_offset_q_win = qtgui.RangeWidget(self._gui_dc_offset_q_range, self.set_gui_dc_offset_q, "Q DC Offset", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._gui_dc_offset_q_win, 1, 6, 1, 2)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(6, 8):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._gui_dc_offset_i_range = qtgui.Range(-1.0, 1.0, (1.0 / 2048.0), dc_offset_i, 200)
        self._gui_dc_offset_i_win = qtgui.RangeWidget(self._gui_dc_offset_i_range, self.set_gui_dc_offset_i, "I DC Offset", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._gui_dc_offset_i_win, 1, 4, 1, 2)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(4, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.rational_resampler_xxx_0 = filter.rational_resampler_ccc(
                interpolation=1,
                decimation=5,
                taps=[],
                fractional_bw=0)
        self.qtgui_waterfall_sink_x_0 = qtgui.waterfall_sink_c(
            8192, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            gui_rx_frequency, #fc
            gui_rx_sample_rate, #bw
            "", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_waterfall_sink_x_0.set_update_time(0.10)
        self.qtgui_waterfall_sink_x_0.enable_grid(False)
        self.qtgui_waterfall_sink_x_0.enable_axis_labels(True)



        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_waterfall_sink_x_0.set_color_map(i, colors[i])
            self.qtgui_waterfall_sink_x_0.set_line_alpha(i, alphas[i])

        self.qtgui_waterfall_sink_x_0.set_intensity_range(-140, 10)

        self._qtgui_waterfall_sink_x_0_win = sip.wrapinstance(self.qtgui_waterfall_sink_x_0.qwidget(), Qt.QWidget)

        self.top_grid_layout.addWidget(self._qtgui_waterfall_sink_x_0_win, 2, 5, 5, 5)
        for r in range(2, 7):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(5, 10):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_freq_sink_x_0 = qtgui.freq_sink_c(
            8192, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            gui_rx_frequency, #fc
            gui_rx_sample_rate, #bw
            "", #name
            1,
            None # parent
        )
        self.qtgui_freq_sink_x_0.set_update_time(0.10)
        self.qtgui_freq_sink_x_0.set_y_axis((-140), 10)
        self.qtgui_freq_sink_x_0.set_y_label('Relative Gain', 'dB')
        self.qtgui_freq_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.qtgui_freq_sink_x_0.enable_autoscale(False)
        self.qtgui_freq_sink_x_0.enable_grid(False)
        self.qtgui_freq_sink_x_0.set_fft_average(0.1)
        self.qtgui_freq_sink_x_0.enable_axis_labels(True)
        self.qtgui_freq_sink_x_0.enable_control_panel(False)
        self.qtgui_freq_sink_x_0.set_fft_window_normalized(False)



        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_freq_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_freq_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_freq_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_freq_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_freq_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_freq_sink_x_0_win = sip.wrapinstance(self.qtgui_freq_sink_x_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_freq_sink_x_0_win, 2, 0, 5, 5)
        for r in range(2, 7):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 5):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.osmosdr_source_0 = osmosdr.source(
            args="numchan=" + str(1) + " " + bladerf_args
        )
        self.osmosdr_source_0.set_time_unknown_pps(osmosdr.time_spec_t())
        self.osmosdr_source_0.set_sample_rate(gui_rx_sample_rate)
        self.osmosdr_source_0.set_center_freq(gui_rx_frequency, 0)
        self.osmosdr_source_0.set_freq_corr(0, 0)
        self.osmosdr_source_0.set_dc_offset_mode(2, 0)
        self.osmosdr_source_0.set_iq_balance_mode(2, 0)
        self.osmosdr_source_0.set_gain_mode(True, 0)
        self.osmosdr_source_0.set_gain(gui_rx_lna_gain, 0)
        self.osmosdr_source_0.set_if_gain(20, 0)
        self.osmosdr_source_0.set_bb_gain(gui_rx_vga_gain, 0)
        self.osmosdr_source_0.set_antenna('', 0)
        self.osmosdr_source_0.set_bandwidth(gui_rx_bandwidth, 0)
        self._gui_bladerf_args_tool_bar = Qt.QToolBar(self)

        if None:
            self._gui_bladerf_args_formatter = None
        else:
            self._gui_bladerf_args_formatter = lambda x: str(x)

        self._gui_bladerf_args_tool_bar.addWidget(Qt.QLabel("bladeRF arguments"))
        self._gui_bladerf_args_label = Qt.QLabel(str(self._gui_bladerf_args_formatter(self.gui_bladerf_args)))
        self._gui_bladerf_args_tool_bar.addWidget(self._gui_bladerf_args_label)
        self.top_grid_layout.addWidget(self._gui_bladerf_args_tool_bar, 11, 0, 1, 10)
        for r in range(11, 12):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 10):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.blocks_float_to_complex_0 = blocks.float_to_complex(1)
        self.blocks_complex_to_float_0 = blocks.complex_to_float(1)
        self.blocks_add_const_vxx_0_0 = blocks.add_const_ff(gui_dc_offset_q)
        self.blocks_add_const_vxx_0 = blocks.add_const_ff(gui_dc_offset_i)
        self.audio_sink_0 = audio.sink(48000,  "Speakers (Audioengine 2+)", True)
        self.analog_fm_demod_cf_0 = analog.fm_demod_cf(
        	channel_rate=384e3,
        	audio_decim=8,
        	deviation=75000,
        	audio_pass=16000,
        	audio_stop=20000,
        	gain=1.0,
        	tau=(75e-6),
        )


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_fm_demod_cf_0, 0), (self.audio_sink_0, 0))
        self.connect((self.blocks_add_const_vxx_0, 0), (self.blocks_float_to_complex_0, 0))
        self.connect((self.blocks_add_const_vxx_0_0, 0), (self.blocks_float_to_complex_0, 1))
        self.connect((self.blocks_complex_to_float_0, 0), (self.blocks_add_const_vxx_0, 0))
        self.connect((self.blocks_complex_to_float_0, 1), (self.blocks_add_const_vxx_0_0, 0))
        self.connect((self.blocks_float_to_complex_0, 0), (self.qtgui_freq_sink_x_0, 0))
        self.connect((self.blocks_float_to_complex_0, 0), (self.qtgui_waterfall_sink_x_0, 0))
        self.connect((self.blocks_float_to_complex_0, 0), (self.rational_resampler_xxx_0, 0))
        self.connect((self.osmosdr_source_0, 0), (self.blocks_complex_to_float_0, 0))
        self.connect((self.rational_resampler_xxx_0, 0), (self.analog_fm_demod_cf_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "bladeRF_rx")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_buflen(self):
        return self.buflen

    def set_buflen(self, buflen):
        self.buflen = buflen
        self.set_bladerf_args("bladerf=" + self.bladerf_selection + ",buffers=" + str(self.num_buffers) + ",buflen=" + str(self.buflen) + ",num_xfers=" + str(self.num_xfers) + ",verbosity="+self.verbosity)

    def get_dc_offset_i(self):
        return self.dc_offset_i

    def set_dc_offset_i(self, dc_offset_i):
        self.dc_offset_i = dc_offset_i
        self.set_gui_dc_offset_i(self.dc_offset_i)

    def get_dc_offset_q(self):
        return self.dc_offset_q

    def set_dc_offset_q(self, dc_offset_q):
        self.dc_offset_q = dc_offset_q
        self.set_gui_dc_offset_q(self.dc_offset_q)

    def get_instance(self):
        return self.instance

    def set_instance(self, instance):
        self.instance = instance
        self.set_bladerf_selection(str(self.instance) if self.serial == "" else self.serial)

    def get_num_buffers(self):
        return self.num_buffers

    def set_num_buffers(self, num_buffers):
        self.num_buffers = num_buffers
        self.set_bladerf_args("bladerf=" + self.bladerf_selection + ",buffers=" + str(self.num_buffers) + ",buflen=" + str(self.buflen) + ",num_xfers=" + str(self.num_xfers) + ",verbosity="+self.verbosity)

    def get_num_xfers(self):
        return self.num_xfers

    def set_num_xfers(self, num_xfers):
        self.num_xfers = num_xfers
        self.set_bladerf_args("bladerf=" + self.bladerf_selection + ",buffers=" + str(self.num_buffers) + ",buflen=" + str(self.buflen) + ",num_xfers=" + str(self.num_xfers) + ",verbosity="+self.verbosity)

    def get_rx_bandwidth(self):
        return self.rx_bandwidth

    def set_rx_bandwidth(self, rx_bandwidth):
        self.rx_bandwidth = rx_bandwidth
        self.set_gui_rx_bandwidth(self.rx_bandwidth)

    def get_rx_frequency(self):
        return self.rx_frequency

    def set_rx_frequency(self, rx_frequency):
        self.rx_frequency = rx_frequency
        self.set_gui_rx_frequency(self.rx_frequency)

    def get_rx_lna_gain(self):
        return self.rx_lna_gain

    def set_rx_lna_gain(self, rx_lna_gain):
        self.rx_lna_gain = rx_lna_gain
        self.set_gui_rx_lna_gain(self.rx_lna_gain)

    def get_rx_sample_rate(self):
        return self.rx_sample_rate

    def set_rx_sample_rate(self, rx_sample_rate):
        self.rx_sample_rate = rx_sample_rate
        self.set_gui_rx_sample_rate(self.rx_sample_rate)

    def get_rx_vga_gain(self):
        return self.rx_vga_gain

    def set_rx_vga_gain(self, rx_vga_gain):
        self.rx_vga_gain = rx_vga_gain
        self.set_gui_rx_vga_gain(self.rx_vga_gain)

    def get_serial(self):
        return self.serial

    def set_serial(self, serial):
        self.serial = serial
        self.set_bladerf_selection(str(self.instance) if self.serial == "" else self.serial)

    def get_verbosity(self):
        return self.verbosity

    def set_verbosity(self, verbosity):
        self.verbosity = verbosity
        self.set_bladerf_args("bladerf=" + self.bladerf_selection + ",buffers=" + str(self.num_buffers) + ",buflen=" + str(self.buflen) + ",num_xfers=" + str(self.num_xfers) + ",verbosity="+self.verbosity)

    def get_bladerf_selection(self):
        return self.bladerf_selection

    def set_bladerf_selection(self, bladerf_selection):
        self.bladerf_selection = bladerf_selection
        self.set_bladerf_args("bladerf=" + self.bladerf_selection + ",buffers=" + str(self.num_buffers) + ",buflen=" + str(self.buflen) + ",num_xfers=" + str(self.num_xfers) + ",verbosity="+self.verbosity)

    def get_bladerf_args(self):
        return self.bladerf_args

    def set_bladerf_args(self, bladerf_args):
        self.bladerf_args = bladerf_args
        self.set_gui_bladerf_args(self.bladerf_args)

    def get_gui_rx_vga_gain(self):
        return self.gui_rx_vga_gain

    def set_gui_rx_vga_gain(self, gui_rx_vga_gain):
        self.gui_rx_vga_gain = gui_rx_vga_gain
        self.osmosdr_source_0.set_bb_gain(self.gui_rx_vga_gain, 0)

    def get_gui_rx_sample_rate(self):
        return self.gui_rx_sample_rate

    def set_gui_rx_sample_rate(self, gui_rx_sample_rate):
        self.gui_rx_sample_rate = gui_rx_sample_rate
        self.osmosdr_source_0.set_sample_rate(self.gui_rx_sample_rate)
        self.qtgui_freq_sink_x_0.set_frequency_range(self.gui_rx_frequency, self.gui_rx_sample_rate)
        self.qtgui_waterfall_sink_x_0.set_frequency_range(self.gui_rx_frequency, self.gui_rx_sample_rate)

    def get_gui_rx_lna_gain(self):
        return self.gui_rx_lna_gain

    def set_gui_rx_lna_gain(self, gui_rx_lna_gain):
        self.gui_rx_lna_gain = gui_rx_lna_gain
        self._gui_rx_lna_gain_callback(self.gui_rx_lna_gain)
        self.osmosdr_source_0.set_gain(self.gui_rx_lna_gain, 0)

    def get_gui_rx_frequency(self):
        return self.gui_rx_frequency

    def set_gui_rx_frequency(self, gui_rx_frequency):
        self.gui_rx_frequency = gui_rx_frequency
        self.osmosdr_source_0.set_center_freq(self.gui_rx_frequency, 0)
        self.qtgui_freq_sink_x_0.set_frequency_range(self.gui_rx_frequency, self.gui_rx_sample_rate)
        self.qtgui_waterfall_sink_x_0.set_frequency_range(self.gui_rx_frequency, self.gui_rx_sample_rate)

    def get_gui_rx_bandwidth(self):
        return self.gui_rx_bandwidth

    def set_gui_rx_bandwidth(self, gui_rx_bandwidth):
        self.gui_rx_bandwidth = gui_rx_bandwidth
        self.osmosdr_source_0.set_bandwidth(self.gui_rx_bandwidth, 0)

    def get_gui_dc_offset_q(self):
        return self.gui_dc_offset_q

    def set_gui_dc_offset_q(self, gui_dc_offset_q):
        self.gui_dc_offset_q = gui_dc_offset_q
        self.blocks_add_const_vxx_0_0.set_k(self.gui_dc_offset_q)

    def get_gui_dc_offset_i(self):
        return self.gui_dc_offset_i

    def set_gui_dc_offset_i(self, gui_dc_offset_i):
        self.gui_dc_offset_i = gui_dc_offset_i
        self.blocks_add_const_vxx_0.set_k(self.gui_dc_offset_i)

    def get_gui_bladerf_args(self):
        return self.gui_bladerf_args

    def set_gui_bladerf_args(self, gui_bladerf_args):
        self.gui_bladerf_args = gui_bladerf_args
        Qt.QMetaObject.invokeMethod(self._gui_bladerf_args_label, "setText", Qt.Q_ARG("QString", str(self._gui_bladerf_args_formatter(self.gui_bladerf_args))))



def argument_parser():
    description = 'A simple RX-only GUI that demonstrates the usage of various RX controls.'
    parser = ArgumentParser(description=description)
    parser.add_argument(
        "--dc-offset-i", dest="dc_offset_i", type=eng_float, default=eng_notation.num_to_str(float(0)),
        help="Set DC offset compensation for I channel [default=%(default)r]")
    parser.add_argument(
        "--dc-offset-q", dest="dc_offset_q", type=eng_float, default=eng_notation.num_to_str(float(0)),
        help="Set DC offset compensation for Q channel [default=%(default)r]")
    parser.add_argument(
        "--instance", dest="instance", type=intx, default=0,
        help="Set 0-indexed device instance describing device to use. Ignored if a serial-number is provided. [default=%(default)r]")
    parser.add_argument(
        "--num-buffers", dest="num_buffers", type=intx, default=16,
        help="Set Number of buffers to use [default=%(default)r]")
    parser.add_argument(
        "--num-xfers", dest="num_xfers", type=intx, default=8,
        help="Set Number of maximum in-flight USB transfers. Should be <= (num-buffers / 2). [default=%(default)r]")
    parser.add_argument(
        "-b", "--rx-bandwidth", dest="rx_bandwidth", type=eng_float, default=eng_notation.num_to_str(float(1.5e6)),
        help="Set Bandwidth [default=%(default)r]")
    parser.add_argument(
        "-f", "--rx-frequency", dest="rx_frequency", type=eng_float, default=eng_notation.num_to_str(float(96.9e6)),
        help="Set Frequency [default=%(default)r]")
    parser.add_argument(
        "-l", "--rx-lna-gain", dest="rx_lna_gain", type=intx, default=6,
        help="Set RX LNA Gain [default=%(default)r]")
    parser.add_argument(
        "-s", "--rx-sample-rate", dest="rx_sample_rate", type=eng_float, default=eng_notation.num_to_str(float(1.92e6)),
        help="Set Sample Rate [default=%(default)r]")
    parser.add_argument(
        "-g", "--rx-vga-gain", dest="rx_vga_gain", type=intx, default=30,
        help="Set RX VGA1 + VGA2 Gain [default=%(default)r]")
    return parser


def main(top_block_cls=bladeRF_rx, options=None):
    if options is None:
        options = argument_parser().parse_args()

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls(dc_offset_i=options.dc_offset_i, dc_offset_q=options.dc_offset_q, instance=options.instance, num_buffers=options.num_buffers, num_xfers=options.num_xfers, rx_bandwidth=options.rx_bandwidth, rx_frequency=options.rx_frequency, rx_lna_gain=options.rx_lna_gain, rx_sample_rate=options.rx_sample_rate, rx_vga_gain=options.rx_vga_gain)

    tb.start()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
