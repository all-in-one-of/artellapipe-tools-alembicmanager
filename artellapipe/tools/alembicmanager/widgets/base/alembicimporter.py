#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains implementation for Alembic Importer
"""

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import json
import logging.config
from functools import partial

from Qt.QtCore import *
from Qt.QtWidgets import *

from tpPyUtils import decorators, python

import tpDccLib as tp

from tpQtLib.core import base
from tpQtLib.widgets import splitters

import artellapipe.register
from artellapipe.utils import resource
from artellapipe.libs.alembic.core import alembic

if tp.is_maya():
    import tpMayaLib as maya


LOGGER = logging.getLogger()


class AlembicImporter(base.BaseWidget, object):

    showOk = Signal(str)

    def __init__(self, project, parent=None):

        self._project = project
        super(AlembicImporter, self).__init__(parent=parent)

    def ui(self):
        super(AlembicImporter, self).ui()

        buttons_layout = QGridLayout()
        self.main_layout.addLayout(buttons_layout)

        shot_name_lbl = QLabel('Shot Name: ')
        self._shot_line = QLineEdit()
        buttons_layout.addWidget(shot_name_lbl, 1, 0, 1, 1, Qt.AlignRight)
        buttons_layout.addWidget(self._shot_line, 1, 1)
        shot_name_lbl.setVisible(False)
        self._shot_line.setVisible(False)

        folder_icon = resource.ResourceManager().icon('folder')
        alembic_path_layout = QHBoxLayout()
        alembic_path_layout.setContentsMargins(2, 2, 2, 2)
        alembic_path_layout.setSpacing(2)
        alembic_path_widget = QWidget()
        alembic_path_widget.setLayout(alembic_path_layout)
        alembic_path_lbl = QLabel('Alembic File: ')
        self._alembic_path_line = QLineEdit()
        self._alembic_path_line.setReadOnly(True)
        self._alembic_path_btn = QPushButton()
        self._alembic_path_btn.setIcon(folder_icon)
        self._alembic_path_btn.setIconSize(QSize(18, 18))
        self._alembic_path_btn.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0); border: 0px solid rgba(255,255,255,0);")
        alembic_path_layout.addWidget(self._alembic_path_line)
        alembic_path_layout.addWidget(self._alembic_path_btn)
        buttons_layout.addWidget(alembic_path_lbl, 2, 0, 1, 1, Qt.AlignRight)
        buttons_layout.addWidget(alembic_path_widget, 2, 1)

        import_mode_layout = QHBoxLayout()
        import_mode_layout.setContentsMargins(2, 2, 2, 2)
        import_mode_layout.setSpacing(2)
        import_mode_widget = QWidget()
        import_mode_widget.setLayout(import_mode_layout)
        import_mode_lbl = QLabel('Import mode: ')
        self._create_radio = QRadioButton('Create')
        self._add_radio = QRadioButton('Add')
        self._merge_radio = QRadioButton('Merge')
        self._create_radio.setChecked(True)
        import_mode_layout.addWidget(self._create_radio)
        import_mode_layout.addWidget(self._add_radio)
        import_mode_layout.addWidget(self._merge_radio)
        buttons_layout.addWidget(import_mode_lbl, 3, 0, 1, 1, Qt.AlignRight)
        buttons_layout.addWidget(import_mode_widget, 3, 1)
        import_mode_lbl.setVisible(False)
        import_mode_widget.setVisible(False)

        self._auto_display_lbl = QLabel('Auto Display Smooth?: ')
        self._auto_smooth_display = QCheckBox()
        self._auto_smooth_display.setChecked(True)
        buttons_layout.addWidget(self._auto_display_lbl, 4, 0, 1, 1, Qt.AlignRight)
        buttons_layout.addWidget(self._auto_smooth_display, 4, 1)

        if tp.is_maya():
            maya_gpu_cache_lbl = QLabel('Import Alembic as GPU Cache?')
            self._maya_gpu_cache_cbx = QCheckBox()
            self._maya_gpu_cache_cbx.setChecked(True)
            buttons_layout.addWidget(maya_gpu_cache_lbl, 5, 0, 1, 1, Qt.AlignRight)
            buttons_layout.addWidget(self._maya_gpu_cache_cbx, 5, 1)
        elif tp.is_houdini():
            hou_archive_abc_node_lbl = QLabel('Import Alembic as Archive?')
            self._hou_archive_abc_node_cbx = QCheckBox()
            buttons_layout.addWidget(hou_archive_abc_node_lbl, 5, 0, 1, 1, Qt.AlignRight)
            buttons_layout.addWidget(self._hou_archive_abc_node_cbx, 5, 1)

        self.main_layout.addLayout(splitters.SplitterLayout())

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(2, 2, 2, 2)
        buttons_layout.setSpacing(2)
        self.main_layout.addLayout(buttons_layout)
        self._import_btn = QPushButton('Import')
        self._import_btn.setIcon(resource.ResourceManager().icon('import'))
        self._import_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._reference_btn = QPushButton('Reference')
        self._reference_btn.setIcon(resource.ResourceManager().icon('reference'))
        self._reference_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        buttons_layout.addWidget(self._import_btn)
        buttons_layout.addWidget(self._reference_btn)

        if tp.is_houdini():
            self._reference_btn.setEnabled(False)

    def setup_signals(self):
        self._alembic_path_btn.clicked.connect(self._on_browse_alembic)
        self._import_btn.clicked.connect(self._on_import_alembic)
        self._reference_btn.clicked.connect(partial(self._on_import_alembic, True))

    @classmethod
    @decorators.abstractmethod
    def import_alembic(cls, project, alembic_path, parent=None, fix_path=False):
        """
        Imports Alembic in current DCC scene
        :param project: ArtellaProject
        :param alembic_path: str
        :param parent: object
        :param fix_path: bool
        :return: bool
        """

        raise NotImplementedError('import_alembic function not implemented for {}!'.format(cls.__name__))

    @staticmethod
    def reference_alembic(project, alembic_path, namespace=None, fix_path=False):
        """
        References alembic file in current DCC scene
        :param project: ArtellaProject
        :param alembic_path: str
        :param namespace: str
        :param fix_path: bool
        """

        if not alembic_path or not os.path.isfile(alembic_path):
            LOGGER.warning('Alembic file {} does not exits!'.format(alembic_path))
            return None

        abc_name = os.path.basename(alembic_path).split('.')[0]
        tag_json_file = os.path.join(
            os.path.dirname(alembic_path), os.path.basename(alembic_path).replace('.abc', '_abc.info'))
        if not os.path.isfile(tag_json_file):
            LOGGER.warning('No Alembic Info file found!')
            return

        with open(tag_json_file, 'r') as f:
            tag_info = json.loads(f.read())
        if not tag_info:
            LOGGER.warning('No Alembic Info loaded!')
            return

        root = tp.Dcc.create_empty_group(name=abc_name)
        AlembicImporter._add_tag_info_data(project, tag_info, root)
        sel = [root]
        sel = sel or None

        if not namespace:
            namespace = abc_name

        new_nodes = alembic.reference_alembic(
            project=project, alembic_file=alembic_path, namespace=namespace, fix_path=fix_path)
        if not new_nodes:
            LOGGER.warning('Error while reference Alembic file: {}'.format(alembic_path))
            return
        for obj in new_nodes:
            if not tp.Dcc.object_exists(obj):
                continue
            if not tp.Dcc.node_type(obj) == 'transform':
                continue
            obj_parent = tp.Dcc.node_parent(obj)
            if obj_parent:
                continue
            tp.Dcc.set_parent(obj, sel[0])
        tp.Dcc.select_object(sel[0])

        new_nodes.insert(0, sel[0])

        # After parenting referenced nodes, full path changes, here we update node paths
        if tp.is_maya():
            new_paths = list()
            for n in new_nodes:
                if tp.Dcc.object_exists(n):
                    new_paths.append(n)
                else:
                    if n.startswith('|'):
                        new_paths.append('{}{}'.format(sel[0], n))
                    else:
                        new_paths.append('{}|{}'.format(sel[0], n))
            return new_paths

        return new_nodes

    @staticmethod
    def _add_tag_info_data(project, tag_info, attr_node):
        """
        Internal function that updates the tag info of the Alembic node
        :param project: ArtellaProject
        :param tag_info: dict
        :param attr_node: str
        """

        if not tp.Dcc.attribute_exists(node=attr_node, attribute_name='tag_info'):
            tp.Dcc.add_string_attribute(node=attr_node, attribute_name='tag_info', keyable=True)
        tp.Dcc.set_string_attribute_value(node=attr_node, attribute_name='tag_info', attribute_value=str(tag_info))

    def refresh(self):
        """
        Function that update necessary info of the tool
        """

        self._refresh_shot_name()

    def _refresh_shot_name(self):
        """
        Internal function that updates the shot name QLineEdit text
        """

        shot_name = 'Undefined'
        current_scene = tp.Dcc.scene_path()
        if current_scene:
            current_scene = os.path.basename(current_scene)

        shot_regex = self._project.get_shot_name_regex()
        m = shot_regex.match(current_scene)
        if m:
            shot_name = m.group(1)

        self._shot_line.setText(shot_name)

    def _on_browse_alembic(self):
        """
        Internal callback function that is called when Browse Alembic File button is clicked
        """

        shot_name = self._shot_line.text()
        abc_folder = os.path.normpath(os.path.join(
            self._project.get_path(), shot_name)) if shot_name != 'unresolved' else self._project.get_path()

        pattern = 'Alembic Files (*.abc)'
        if tp.is_houdini():
            pattern = '*.abc'
        abc_file = tp.Dcc.select_file_dialog(
            title='Select Alembic to Import', start_directory=abc_folder, pattern=pattern)
        if abc_file:
            self._alembic_path_line.setText(abc_file)

    def _on_import_alembic(self, as_reference=False):
        """
        Internal callback function that is called when Import/Reference Alembic button is clicked
        :param as_reference: bool
        """

        abc_file = self._alembic_path_line.text()
        if not abc_file or not os.path.isfile(abc_file):
            tp.Dcc.confirm_dialog(
                title='Error', message='No Alembic File is selected or file is not currently available in disk')
            return None

        abc_name = os.path.basename(abc_file).split('.')[0]
        tag_json_file = os.path.join(os.path.dirname(abc_file), os.path.basename(abc_file).replace('.abc', '_abc.info'))
        valid_tag_info = True
        if os.path.isfile(tag_json_file):
            with open(tag_json_file, 'r') as f:
                tag_info = json.loads(f.read())
            if not tag_info:
                LOGGER.warning('No Alembic Info loaded!')
                valid_tag_info = False
        else:
            LOGGER.warning('No Alembic Info file found!')
            valid_tag_info = False

        if as_reference:
            reference_nodes = self._reference_alembic(alembic_file=abc_file, namespace=abc_name)
        else:
            reference_nodes = self._import_alembic(
                alembic_file=abc_file, valid_tag_info=valid_tag_info)
        reference_nodes = python.force_list(reference_nodes)

        added_tag = False
        for key in tag_info.keys():
            if reference_nodes:
                for obj in reference_nodes:
                    short_obj = tp.Dcc.node_short_name(obj)
                    if key == short_obj:
                        self._add_tag_info_data(self._project, tag_info[key], obj)
                        added_tag = True

        if not added_tag:
            self._add_tag_info_data(self._project, tag_info, reference_nodes[0])

        if reference_nodes:
            if as_reference:
                self.showOk.emit('Alembic file referenced successfully!')
            else:
                self.showOk.emit('Alembic file imported successfully!')

        return reference_nodes

    @classmethod
    def _create_alembic_group(cls, group_name):
        """
        Internal function that creates root gruop for Alembic Node
        :return: str
        """

        root = tp.Dcc.create_empty_group(name=group_name)

        return root

    def _import_alembic(self, alembic_file, valid_tag_info, nodes=None, parent=None):
        """
        Internal callback function that imports given alembic file
        :param alembic_file: str
        :param valid_tag_info: bool
        :param nodes: list
        :param parent: object
        :return:
        """

        if valid_tag_info:
            res = alembic.import_alembic(
                project=self._project, alembic_file=alembic_file, mode='import', nodes=nodes, parent=parent)
        else:
            res = alembic.import_alembic(project=self._project, alembic_file=alembic_file, mode='import', parent=parent)

        return res

    def _reference_alembic(self, alembic_file, namespace, parent):
        """
        Internal function that references given alembic file
        :param alembic_file: str
        :param namespace: str
        :return:
        """

        all_nodes = alembic.reference_alembic(project=self._project, alembic_file=alembic_file, namespace=namespace)
        if not all_nodes:
            LOGGER.warning('Error while reference Alembic file: {}'.format(alembic_file))
            return
        for obj in all_nodes:
            if not tp.Dcc.object_exists(obj):
                continue
            if not tp.Dcc.node_type(obj) == 'transform':
                continue
            obj_parent = tp.Dcc.node_parent(obj)
            if obj_parent:
                continue
            tp.Dcc.set_parent(node=obj, parent=parent)

        return all_nodes


artellapipe.register.register_class('AlembicImporter', AlembicImporter)
