""" Tests for the deb_example module. """
from threading import Lock
from pathlib import Path
import unittest

import numpy as np
import tensorflow as tf

from ebop_maven import deb_example

# pylint: disable=invalid-name, too-many-public-methods, line-too-long, protected-access, too-many-locals
class Test_deb_example(unittest.TestCase):
    """ Tests for the deb_example module """
    # These tests may fiddle with the description so should not be run parallel
    lock = Lock()

    #
    #   TEST create_mags_key(mags_bins: int, mags_wrap_phse: float) -> str
    #
    def test_create_mags_key_integers(self):
        """ Tests create_map_key() make sure that int values are formatted as mags_int_float"""
        self.assertEqual("mags_1024_2.0", deb_example.create_mags_key(1024, 2))

    def test_create_mags_key_floats(self):
        """ Tests create_map_key() make sure that float values are formatted as mags_int_float"""
        self.assertEqual("mags_1024_0.2", deb_example.create_mags_key(1024.0, 0.2))
        self.assertEqual("mags_1024_0.75", deb_example.create_mags_key(1024.1, 0.75))
        self.assertEqual("mags_1024_0.666", deb_example.create_mags_key(1024.9, 0.666))


    #
    #   TEST create_map_func(mags_bins: int, mags_wrap_phse: float,
    #                        ext_features: List[str], labels: List[str],
    #                        noise_stddev: Callable->float, roll_steps: Callable->int) -> Callable
    #
    def test_create_map_func_default_behaviour(self):
        """ Test that the resulting map_func accurately deserializes a deb_example """
        with self.__class__.lock:
            # Set up a feature (light-curve) amd labels and with tracable values
            input_labels = { k: v for v, k in enumerate(deb_example.labels_and_scales) }
            input_lc_feature =  { deb_example.default_mags_key: np.arange(deb_example.default_mags_bins) }
            input_ext_features = { "phiS": 0.6, "dS_over_dP": 0.96 }
            deb = deb_example.serialize("t1", input_labels, input_lc_feature, input_ext_features)

            # Execute a graph instance of the map_func to mimic a Dateset pipeline.
            # map_parse_fn = deb_example.create_map_func()
            map_parse_fn = tf.function(deb_example.create_map_func())
            ((lc_feature, ext_features), labels) = map_parse_fn(deb)

            # lc output should be a Tensor of shape (len, 1) with content unchanged from the input
            self.assertEqual(lc_feature.shape, (len(input_lc_feature[deb_example.default_mags_key]), 1))
            for lb_bin, input_lc_bin in zip(lc_feature.numpy()[:, 0],
                                            input_lc_feature[deb_example.default_mags_key]):
                self.assertEqual(lb_bin, input_lc_bin)

            # features output should be a Tensor of the shape (#features, 1)
            self.assertEqual(ext_features.shape, (len(deb_example.extra_features_and_defaults), 1))
            for feature, exp_value in zip(ext_features.numpy(), input_ext_features.values()):
                self.assertEqual(feature, exp_value)

            # labels output should be a list of Tensors of length #labels
            # Assert they have been scaled and are in correct order
            self.assertEqual(len(labels), len(deb_example.labels_and_scales))
            self.assertIsInstance(labels, list)
            exp_values = [v * s for v, s in zip(input_labels.values(), deb_example.labels_and_scales.values())]
            for label, exp_value in zip(labels, exp_values):
                # Some loss of fidelity in encoding/decoding a tf.Tensor so can't do exact assert
                self.assertAlmostEqual(label.numpy(), exp_value, 6)

    def test_create_map_func_with_selected_ext_features(self):
        """ Test that the resulting map_func deserializes a deb_example with subset of ext_features """
        with self.__class__.lock:
            # Set up a feature (light-curve) amd labels and with tracable values
            input_labels_and_scales = deb_example.labels_and_scales.copy()
            input_labels = { k: v for v, k in enumerate(input_labels_and_scales) }
            input_mags_feature =  { deb_example.default_mags_key: np.arange(deb_example.default_mags_bins) }
            input_ext_features = { "phiS": 0.6, "dS_over_dP": 0.96 }
            deb = deb_example.serialize("t1", input_labels, input_mags_feature, input_ext_features)

            # We're going to request a shuffled subset of the ext_features
            request_features = [f for f in input_ext_features if f not in ["phiS"]]

            # Execute a graph instance of the map_func to mimic a Dateset pipeline.
            # map_parse_fn = deb_example.create_map_func()
            map_parse_fn = tf.function(deb_example.create_map_func(ext_features=request_features))
            ((mags_feature, ext_features), labels) = map_parse_fn(deb)

            # features output should be a Tensor of the shape (#request_features, 1)
            self.assertEqual(ext_features.shape, (len(request_features), 1))
            exp_values = [input_ext_features[e] for e in request_features]
            for feature, exp_value in zip(ext_features.numpy(), exp_values):
                self.assertEqual(feature, exp_value)

            # Check no effect on the other values
            self.assertEqual(mags_feature.shape, (deb_example.default_mags_bins, 1))
            self.assertEqual(len(labels), len(input_labels))

    def test_create_map_func_with_selected_labels(self):
        """ Test that the resulting map_func deserializes a deb_example with subset of labels """
        with self.__class__.lock:
            # Set up a feature (light-curve) amd labels and with tracable values
            input_labels_and_scales = deb_example.labels_and_scales.copy()
            input_labels = { k: v for v, k in enumerate(input_labels_and_scales) }
            input_lc_feature =  { deb_example.default_mags_key: np.arange(deb_example.default_mags_bins) }
            input_ext_features = { "phiS": 0.6, "dS_over_dP": 0.96 }
            deb = deb_example.serialize("t1", input_labels, input_lc_feature, input_ext_features)

            # We're going to request a shuffled subset - we should only get these and in this order
            request_labels = [k for k in input_labels_and_scales if k not in ["J"]]
            np.random.shuffle(request_labels)

            # Execute a graph instance of the map_func to mimic a Dateset pipeline.
            # map_parse_fn = deb_example.create_map_func()
            map_parse_fn = tf.function(deb_example.create_map_func(labels=request_labels))
            (_, labels) = map_parse_fn(deb)

            # labels output should be a list of Tensors of length #request_labels
            # Assert they have been scaled and are in request_labels order
            self.assertEqual(len(labels), len(request_labels))
            self.assertIsInstance(labels, list)
            exp_values = [input_labels[l] * input_labels_and_scales[l] for l in request_labels]
            for label, exp_value in zip(labels, exp_values):
                # Some loss of fidelity in encoding/decoding a tf.Tensor so can't do exact assert
                self.assertAlmostEqual(label.numpy(), exp_value, 6)

    def test_create_map_func_with_roll(self):
        """ Tests the created map_func's roll functionality """
        with self.__class__.lock:
            # Set up a feature (light-curve) amd labels and with tracable values
            input_labels = { k: v for v, k in enumerate(deb_example.labels_and_scales) }
            input_lc_feature = { deb_example.default_mags_key: np.arange(deb_example.default_mags_bins) }
            deb = deb_example.serialize("t1", input_labels, input_lc_feature, {})

            for roll_by in [-5, 0, 5]:
                # pylint: disable=cell-var-from-loop
                # Execute a graph instance of the map_func (with roll) to mimic a Dateset pipeline.
                map_parse_fn = tf.function(deb_example.create_map_func(roll_steps=lambda: roll_by))
                ((lc_feature, _), _) = map_parse_fn(deb)

                # Assert that these bins match the input values where they should have been rolled from
                lc_feature = lc_feature.numpy()[:, 0]
                for lb_ix in np.arange(500, 600, 1):
                    self.assertEqual(lc_feature[lb_ix + roll_by],
                                     input_lc_feature[deb_example.default_mags_key][lb_ix])

    def test_create_map_func_with_noise(self):
        """ Tests the created map_func's roll functionality """
        with self.__class__.lock:
            # Set up a feature (light-curve) amd labels and with tracable values
            input_labels = { k: v for v, k in enumerate(deb_example.labels_and_scales) }
            input_lc_feature = { deb_example.default_mags_key: [1] * deb_example.default_mags_bins } # all the same, so stddev==0
            deb = deb_example.serialize("t1", input_labels, input_lc_feature, {})

            # Execute a graph instance of the map_func (with roll) to mimic a Dateset pipeline.
            apply_stddev = 0.01
            map_parse_fn = tf.function(deb_example.create_map_func(noise_stddev=lambda: apply_stddev))
            ((lc_feature, _), _) = map_parse_fn(deb)

            # Assert that stddev of the output lc reflects the noise we applied
            lc_feature = lc_feature.numpy()[:, 0]
            self.assertAlmostEqual(lc_feature.std(), apply_stddev, 3)

    def test_create_map_func_with_random_roll(self):
        """ Tests implementing a random roll_steps func via create_map_func() """
        with self.__class__.lock:
            # Set up a feature (light-curve) amd labels and with tracable values
            input_labels = { k: v for v, k in enumerate(deb_example.labels_and_scales) }
            input_lc_feature = { deb_example.default_mags_key: np.arange(deb_example.default_mags_bins) }
            deb = deb_example.serialize("t1", input_labels, input_lc_feature, {})

            def random_roll():
                """ Create a random roll_steps value """
                return tf.random.uniform([], -100, 101, tf.int32)
            map_parse_fn = tf.function(deb_example.create_map_func(roll_steps=random_roll))

            # Execute map_func a number of times on the same input lc with the random roll.
            # Store the output lcs, which should have different rolls applied to them.
            lc_copy_list = []
            for _ in range(5):

                ((lc_feature, _), _) = map_parse_fn(deb)
                lc_copy_list.append(lc_feature.numpy()[:, 0])

            # There should be variation per bin across the lcs due to random roll_steps value
            first_bins = np.vstack(lc_copy_list)[:, 0]
            print(f"first_bins == {first_bins}")
            self.assertFalse(all(bin == first_bins[0] for bin in first_bins), f"{first_bins}")

    #
    #   TEST iterate_dataset(dataset_files: List[str], mags_bins: int, mags_wrap_phse: float,
    #                        ext_features: List[str], labels: List[str],
    #                        identifiers: List[str], scale_labels: bool)
    #                           -> Generator(ids, mags, features, labels)
    #
    #   iterate_dataset() wraps create_dataset_pipeline() so that gets a workout too
    #
    def test_iterate_dataset_default_args(self):
        """ Tests iterate_dataset(no id filter) -> all rows """
        files = list((Path.cwd() / "datasets/formal-test-dataset/").glob("**/*.tfrecord"))
        (id_val, mrow, frow, lrow) = next(deb_example.iterate_dataset(files))
        # Check the dimensions of whats returned for the first row; should reflect the defaults
        self.assertIsNotNone(id_val)
        self.assertEqual(deb_example.default_mags_bins, mrow.shape[0])
        self.assertEqual(len(deb_example.extra_features_and_defaults), frow.shape[0])
        self.assertEqual(len(deb_example.labels_and_scales), lrow.shape[0])

    def test_iterate_dataset_no_filters(self):
        """ Tests iterate_dataset(no id filter) -> all rows """
        files = list((Path.cwd() / "datasets/formal-test-dataset/").glob("**/*.tfrecord"))
        (_, row_count) = deb_example.create_dataset_pipeline(files)

        iterate_count = 0
        for _ in deb_example.iterate_dataset(files, identifiers=None):
            iterate_count += 1
        self.assertEqual(row_count, iterate_count)

    def test_iterate_dataset_identifers_filtering(self):
        """ Tests iterate_dataset(with id filter) -> selected rows in stored order """
        files = list((Path.cwd() / "datasets/formal-test-dataset/").glob("**/*.tfrecord"))
        identifiers = ["CM Dra", "CW Eri"] # Not in the order they appear in the dataset
        id_vals = []
        for (id_val, _, _, _) in deb_example.iterate_dataset(files, identifiers=identifiers):
            id_vals += [id_val]
        # Only the two rows, yielded in the order they appear in the dataset
        self.assertEqual(["CW Eri", "CM Dra"], id_vals)

    def test_iterate_dataset_all_filters(self):
        """ Tests iterate_dataset(with id, features & labels filter and scaling) -> selected rows """
        files = list((Path.cwd() / "datasets/formal-test-dataset/").glob("**/*.tfrecord"))
        (id_val, mrow, frow, lrow) = next(deb_example.iterate_dataset(files, 4096, 1.0,
                ext_features=["phiS"], labels=["inc"], identifiers=["CW Eri"], scale_labels=True))

        self.assertEqual("CW Eri", id_val)
        self.assertEqual(4096, len(mrow))
        self.assertEqual(1, len(frow))
        self.assertAlmostEqual(0.503, frow[0], 3)   # feature: phiS (dS_over_dP near 1.0)
        self.assertEqual(1, len(lrow))
        self.assertAlmostEqual(0.864, lrow[0], 3)   # label: inc scaled (so inc/100)


    #
    #   TEST read_dataset(dataset_files: List[str], mags_bins: int, mags_wrap_phse: float,
    #                     ext_features: List[str], labels: List[str],
    #                     identifiers: List[str], scale_labels: bool)
    #                       -> (ids, mags, features, labels)
    #
    def test_read_dataset_identifers_filtering(self):
        """ Tests read_dataset(with id & label filters) -> selected rows in given order """
        files = list((Path.cwd() / "datasets/formal-test-dataset/").glob("**/*.tfrecord"))

        identifiers = ["CM Dra", "CW Eri"] # Not in the order they appear in the dataset
        labels = ["L3", "inc"]
        (id_vals, _, _, lrows) = deb_example.read_dataset(files, identifiers=identifiers,
                                                          labels=labels, scale_labels=False)

        # Only the two rows, yielded in the order requested, not the order they're stored in
        # the same with the labels; in the order they are requested
        self.assertEqual(2, len(id_vals))
        self.assertEqual(identifiers[0], id_vals[0])        # CM Dra
        self.assertAlmostEqual(0, lrows[0, 0], 3)           # L3
        self.assertAlmostEqual(89.5514, lrows[0, 1], 3)     # inc
        self.assertEqual(identifiers[1], id_vals[1])        # CW Eri
        self.assertAlmostEqual(-0.0002, lrows[1, 0], 3)     # L3
        self.assertAlmostEqual(86.381, lrows[1, 1], 3)      # inc

    @unittest.skip("only run this interactively as it may take a long time")
    def test_read_dataset_scalability_test(self):
        """ Tests read_dataset(with large dataset) -> data is returned in seconds not minutes/hours """

        # There are approx 116,000 rows in this dataset - should be done in ~20 s
        # As read_dataset() wraps iterate_dataset() this tests both functions' scalability
        files = list((Path.cwd() / "datasets/synthetic-mist-tess-dataset/").glob("**/*.tfrecord"))
        (id_vals, _, _, lrows) = deb_example.read_dataset(files, 4096, 0.75, scale_labels=False)
        self.assertTrue(len(id_vals) > 100000)
        self.assertTrue(len(lrows) > 100000)
        self.assertEqual(len(lrows), len(id_vals))

if __name__ == "__main__":
    unittest.main()
