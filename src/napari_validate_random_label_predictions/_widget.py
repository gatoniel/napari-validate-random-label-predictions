"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""

import napari
import yaml
from magicgui.widgets import FileEdit, Slider, create_widget
from napari.layers import Image, Labels
from napari.types import LabelsData
from qtpy.QtWidgets import QPushButton, QVBoxLayout, QWidget
from skimage.measure import regionprops

VALUES = ["Perfect!", "Needs improvement", "Wrong!"]


def bbox_to_slices(bbox, padding):
    slices = []
    ndim = len(bbox) // 2
    for i in range(ndim):
        slices.append(
            slice(
                max(0, bbox[i] - padding),
                bbox[i + ndim] + padding,
            )
        )
    return tuple(slices)


class ValidateLabelsWidget(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        self.file_edit = FileEdit(label="Label list: ", mode="r")
        self.labels_data = create_widget(annotation=LabelsData)

        self.slider = Slider(
            label="Bbox offset", value=18, min=0, max=100, step=1
        )
        btn = QPushButton("Click me!")
        btn.clicked.connect(self._on_click)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.file_edit.native)
        self.layout().addWidget(self.labels_data.native)
        self.layout().addWidget(self.slider.native)
        self.layout().addWidget(btn)

        self.label_list = None
        self.label_dict = None
        self.label_bboxes = None
        self.new_viewer = None
        self.counter = None

    def _on_click(self):
        with open(self.file_edit.value) as f:
            self.label_list = yaml.full_load(f)
        self.new_file = str(self.file_edit.value).replace(".yaml", "_res.yaml")

        self.label_dict = {}
        self.label_bboxes = {}

        self.new_viewer = napari.Viewer()

        self.data = self.labels_data.value
        regs = regionprops(self.data)

        for reg in regs:
            lbl_id = reg["label"]
            if lbl_id in self.label_list:
                self.label_bboxes[lbl_id] = bbox_to_slices(
                    reg["bbox"], self.slider.value
                )

        self.counter = 0

        self.show_next_label()

        self.new_viewer.bind_key("1")(self.bind_1)
        self.new_viewer.bind_key("2")(self.bind_2)
        self.new_viewer.bind_key("3")(self.bind_3)

        self.new_viewer.text_overlay.visible = True
        self.new_viewer.text_overlay.font_size = 16
        self.new_viewer.text_overlay.color = "white"
        self.new_viewer.text_overlay.text = "\n".join(
            [
                "press on keyboard:",
                "1: perfect",
                "2: ok",
                "3: not good at all",
            ]
        )

    def show_next_label(self):
        # delete all layers in new_viewer
        self.new_viewer.layers.clear()

        try:
            lbl = self.label_list[self.counter]
        except IndexError:
            print("End of label list reached!")
            self.new_viewer.close()
            return

        slices = self.label_bboxes[lbl]
        for layer in self.viewer.layers:
            name = layer.name
            if isinstance(layer, Labels):
                self.new_viewer.add_labels(layer.data[slices], name=name)
            if isinstance(layer, Image):
                self.new_viewer.add_image(layer.data[slices], name=name)
        self.new_viewer.add_labels(
            self.data[slices] == lbl, name="highlighted label"
        )
        self.new_viewer.layers.selection.clear()

    def key_press(self, value):
        lbl = self.label_list[self.counter]
        self.label_dict[lbl] = value

        with open(self.new_file, "w") as f:
            yaml.dump(self.label_dict, f)

        self.counter += 1
        self.show_next_label()

    def reset_choices(self, event=None):
        self.labels_data.reset_choices(event)

    def showEvent(self, event) -> None:
        self.reset_choices()
        return super().showEvent(event)

    def bind_1(self, viewer):
        self.key_press(1)

    def bind_2(self, viewer):
        self.key_press(2)

    def bind_3(self, viewer):
        self.key_press(3)
