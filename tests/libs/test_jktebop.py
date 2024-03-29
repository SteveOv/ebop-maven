""" Unit tests for the jktebop module. """
import os
import unittest
from pathlib import Path
from subprocess import CalledProcessError

import numpy as np

import tests.libs.helpers.lightcurve_helpers as th

from ebop_maven.libs import jktebop
from ebop_maven.libs.jktebop import _prepare_params_for_task
from ebop_maven.libs.jktebop import generate_model_light_curve
from ebop_maven.libs.jktebop import write_task3_in_file, write_light_curve_to_dat_file

# pylint: disable=invalid-name, too-many-public-methods, line-too-long, protected-access
class Testjktebop(unittest.TestCase):
    """ Unit tests for the jktebop module. """
    _prefix = "test_deblib_"
    _task2_params = { # set of valid param/tokens & values for task 2
        "ring": 2,
        "rA_plus_rB": 0.3,  "k": 0.5,
        "inc": 90.,         "qphot": 0.5,
        "ecosw": 0.,        "esinw": 0.,
        "gravA": 0.,        "gravB": 0.,
        "J": 0.8,           "L3": 0.,
        "LDA": "quad",      "LDB": "quad",
        "LDA1": 0.25,       "LDB1": 0.25,
        "LDA2": 0.22,       "LDB2": 0.22,
        "reflA": 0.,        "reflB": 0.,
    }

    _task3_params = { # set of valid param/tokens & values for task 3
        "ring": 3,
        "rA_plus_rB": 0.3,  "k": 0.5,
        "inc": 90.,         "qphot": 0.5,
        "ecosw": 0.,        "esinw": 0.,
        "gravA": 0.,        "gravB": 0.,
        "J": 0.8,           "L3": 0.,
        "LDA": "quad",      "LDB": "quad",
        "LDA1": 0.25,       "LDB1": 0.25,
        "LDA2": 0.22,       "LDB2": 0.22,
        "reflA": 0.,        "reflB": 0.,
        "period": 2.5,
        "primary_epoch": 59876.54321,
        "ecosw_fit": 1,     "esinw_fit": 1,
                            "L3_fit": 1,
        "LDA1_fit": 1,      "LDB1_fit": 1,
        "LDA2_fit": 0,      "LDB2_fit": 0,
        "data_file_name": "cw_eri_s0004.dat"
    }

    @classmethod
    def setUpClass(cls):
        """ Make sure JKTEBOP_DIR is corrected up as tests may modify it. """
        jktebop._jktebop_directory = Path(os.environ.get("JKTEBOP_DIR", "~/jktebop43")).expanduser().absolute()
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        """ Make sure JKTEBOP_DIR is corrected up as tests may modify it. """
        jktebop._jktebop_directory = Path(os.environ.get("JKTEBOP_DIR", "~/jktebop43")).expanduser().absolute()
        return super().tearDownClass()


    #
    # Tests generate_model_light_curve(file_prefix: str,
    #                                  **params) -> np.ndarray
    #
    def test_generate_model_light_curve_args_none(self):
        """ Test generate_model_light_curve(arguments None) raises TypeError """
        self.assertRaises(TypeError, generate_model_light_curve, None, {"rA":2})
        self.assertRaises(TypeError, generate_model_light_curve, self._prefix, None)

    def test_generate_model_light_curve_missing_params(self):
        """ Test generate_model_light_curve(missing params) raises TypeError """
        params = {"rA": 2 } # No mandatory rA_plus_rB params (among many others)
        self.assertRaises(KeyError, generate_model_light_curve, self._prefix, **params)

    def test_generate_model_light_curve_jktebop_error(self):
        """ Test generate_model_light_curve(jktebop fails) raises CalledProcessError """
        params = self._task2_params.copy()
        params["rA_plus_rB"] = 0.9 # max supported up to v43 value is 0.8
        self.assertRaises(CalledProcessError, generate_model_light_curve, self._prefix, **params)

    @unittest.skip("skip on full run as can cause parallel tests to fail")
    def test_generate_model_light_curve_env_variable_incorrect(self):
        """ Test generate_model_light_curve(JKTEBOP_DIR points to wrong loc) ignores others """
        params = self._task2_params.copy()
        jktebop._jktebop_directory = Path.home()
        self.assertRaises(FileNotFoundError, generate_model_light_curve, self._prefix, **params)
        jktebop._jktebop_directory = Path(os.environ.get("JKTEBOP_DIR", "~/jktebop43")).expanduser().absolute()

    def test_generate_model_light_curve_valid_params_only(self):
        """ Test generate_model_light_curve(all necessary params) generates model """
        params = self._task2_params.copy()
        model = generate_model_light_curve(self._prefix, **params)
        self.assertIsNotNone(model)
        self.assertEqual(model.shape[0], 2) # columns
        self.assertTrue(model.shape[1] > 0) # rows

    def test_generate_model_light_curve_valid_params_plus_extras(self):
        """ Test generate_model_light_curve(all necessary params + others) ignores others """
        params = self._task2_params.copy()
        params["another_param_to_be_ignores"] = "anything or nothing"
        model = generate_model_light_curve(self._prefix, **params)
        self.assertIsNotNone(model)
        self.assertEqual(model.shape[0], 2) # columns


    #
    # TESTS write_task3_in_file(file_name, [append_lines], **params)
    #
    def test_write_task3_in_file_args_none_or_wrong_type(self):
        """ Test write_light_curve_to_dat_file(wrong file_name type) raises TypeError """
        self.assertRaises(TypeError, write_task3_in_file, None)
        self.assertRaises(TypeError, write_task3_in_file, "hello")

    def test_write_task3_in_file_missing_params(self):
        """ Test write_light_curve_to_dat_file(missing template params) raises KeyError """
        file_name = th.TEST_DATA_DIR / "any_old_file_will_do.dat"
        self.assertRaises(KeyError, write_task3_in_file, file_name, k=0.5)

    def test_write_task3_in_file_validation_rules(self):
        """ Test write_light_curve_to_dat_file(some invalid param values) raises ValueError """
        file_name = th.TEST_DATA_DIR / "any_old_file_will_do.dat"
        for param, value in [("L3", -0.1),
                             ("rA_plus_rB", 0.9)]:
            params = self._task3_params.copy()
            params[param] = value
            with self.assertRaises(ValueError, msg=f"{param} == {value}"):
                write_task3_in_file(file_name, None, **params)

    def test_write_task3_in_file_full_set_of_params(self):
        """ Test write_light_curve_to_dat_file(missing template params) raises KeyError """
        file_stem = "test_write_task3_in_file_full_set_of_params.3"
        file_name = th.TEST_DATA_DIR / f"{file_stem}.in"
        write_task3_in_file(file_name, **self._task3_params)

        with open(file_name, "r", encoding="utf8") as inf:
            text = inf.read()
            self.assertIn(self._task3_params["LDB"], text)
            self.assertIn(self._task3_params["data_file_name"], text)
            self.assertIn(file_stem, text)

    def test_write_task3_in_file_append_lines(self):
        """ Test write_light_curve_to_dat_file(missing template params) raises KeyError """
        file_name = th.TEST_DATA_DIR / "test_write_task3_in_file_append_lines.3.in"
        append_lines = [ "line 1\n\n", "\n\n\nline 2", "line 3" ]

        write_task3_in_file(file_name, append_lines, **self._task3_params)
        with open(file_name, "r", encoding="utf8") as inf:
            text = inf.read()
            for line in append_lines:
                self.assertIn(line.strip(), text)


    #
    # TESTS write_light_curve_to_dat_file(lc, file_name, [column_names], [column_formats])
    #
    def test_write_light_curve_to_dat_file_args_none_or_wrong_type(self):
        """ Test write_light_curve_to_dat_file(arguments wrong type) raises TypeError """
        lc = th.load_lightcurve("CW Eri")
        file_name = th.TEST_DATA_DIR / "any_old_file_will_do.dat"
        self.assertRaises(TypeError, write_light_curve_to_dat_file, None,   file_name)
        self.assertRaises(TypeError, write_light_curve_to_dat_file, lc,     None)

        lc_array = [lc["time"].value, lc["delta_mag"].value, lc["delta_mag_err"].value]
        self.assertRaises(TypeError, write_light_curve_to_dat_file, lc_array, file_name)
        self.assertRaises(TypeError, write_light_curve_to_dat_file, lc, f"{file_name}")

    def test_write_light_curve_to_dat_file_column_args_not_matching(self):
        """ Test write_light_curve_to_dat_file(column args numbers mismatch) raises ValueError """
        lc = th.load_lightcurve("CW Eri")
        file_name = th.TEST_DATA_DIR / "any_old_file_will_do.dat"
        self.assertRaises(ValueError, write_light_curve_to_dat_file, lc, file_name, ["time"], None)
        self.assertRaises(ValueError, write_light_curve_to_dat_file, lc, file_name, ["time"], ["%.6f", "%.6f"])
        self.assertRaises(ValueError, write_light_curve_to_dat_file, lc, file_name, None, ["%.6f"])
        self.assertRaises(ValueError, write_light_curve_to_dat_file, lc, file_name, ["time", "delta_mag"], ["%.6f"])

    def test_write_light_curve_to_dat_file_default_columns(self):
        """ Test write_light_curve_to_dat_file(using default column & formats)  writes file"""
        lc = th.load_lightcurve("CW Eri")
        file_name = th.TEST_DATA_DIR / "test_write_light_curve_to_dat_file_default_columns.dat"

        write_light_curve_to_dat_file(lc, file_name)

        data = np.loadtxt(file_name, comments="#", delimiter=" ", unpack=True)
        self.assertEqual(data.shape[0], 3)
        self.assertEqual(data.shape[1], len(lc))
        self.assertAlmostEqual(data[0][750], float(lc.iloc[750]["time"].jd)-2.4e6, 6)
        self.assertAlmostEqual(data[1][1000], float(lc.iloc[1000]["delta_mag"].value), 6)

    def test_write_light_curve_to_dat_file_explicit_columns(self):
        """ Test write_light_curve_to_dat_file(explicit columns & formats) writes file """
        lc = th.load_lightcurve("CW Eri")
        file_name = th.TEST_DATA_DIR / "test_write_light_curve_to_dat_file_explicit_columns.dat"

        write_light_curve_to_dat_file(lc,
                                      file_name,
                                      ["time", "sap_flux"],
                                      [lambda t: f"{t.jd:.3f}", "%.3f"])

        data = np.loadtxt(file_name, comments="#", delimiter=" ", unpack=True)
        self.assertEqual(data.shape[0], 2)
        self.assertEqual(data.shape[1], len(lc))
        self.assertAlmostEqual(data[0][250], float(lc.iloc[250]["time"].jd), 3)
        self.assertAlmostEqual(data[1][500], float(lc.iloc[500]["sap_flux"].value), 3)


    #
    # Tests (private) _prepare_params_for_task(task: int,
    #                                          params: dict,
    #                                          [fit_rA_and_rB] = False,
    #                                          [fit_e_and_omega] = False,
    #                                          [calc_refl_coeffs] = False,
    #                                          [in_place] = False)
    #                                               -> [None or dict]
    #
    def test__prepare_params_for_task_args_none(self):
        """ Test _prepare_params_for_task(arguments None) raises TypeError """        
        self.assertRaises(TypeError, _prepare_params_for_task, task=None, params={"rA":2})
        self.assertRaises(TypeError, _prepare_params_for_task, task=2, params=None)

    def test__prepare_params_for_task_fit_flags_with_related_params_missing(self):
        """ Test _prepare_params_for_task(fit_*=True and related params missing) raises KeyError """
        # Setting fit_rA_and_rB==True depends on the rA and rB params
        self.assertRaises(KeyError, _prepare_params_for_task, task=2, fit_rA_and_rB=True,  params={"rB":2})
        self.assertRaises(KeyError, _prepare_params_for_task, task=2, fit_rA_and_rB=True,  params={"rA":2})
        # Setting fit_e_and_omega==True depends on the e and omega params
        self.assertRaises(KeyError, _prepare_params_for_task, task=2, fit_e_and_omega=True,  params={"omega":90})
        self.assertRaises(KeyError, _prepare_params_for_task, task=2, fit_e_and_omega=True,  params={"e":0.1})

    def test__prepare_params_for_task_fit_rA_and_rB_true(self):
        """ Test _prepare_params_for_task(fit_rA_and_rB=True) check params correctly updated """
        params = { "rA": 2, "rB": 1, "rA_plus_rB": 3, "k": 0.5 }
        _prepare_params_for_task(2, params, fit_rA_and_rB=True, in_place=True)
        self.assertEqual(params["rA_plus_rB"], -params["rA"])
        self.assertEqual(params["k"], params["rB"])

    def test__prepare_params_for_task_fit_e_and_omega_true(self):
        """ Test _prepare_params_for_task(fit_e_and_omega=True) check params correctly updated """
        params = { "ecosw": 0., "esinw": 0., "e": 0.1, "omega": 90 }
        _prepare_params_for_task(2, params, fit_e_and_omega=True, in_place=True)
        self.assertEqual(params["ecosw"], 10+params["e"])
        self.assertEqual(params["esinw"], params["omega"])

    def test__prepare_params_for_task_task2_calc_refl_coeffs_true(self):
        """ Test _prepare_params_for_task(task=2, calc_refl_coeffs=True) check params correctly updated """
        params = _prepare_params_for_task(2, { "reflA": 0, "reflB": 0 }, calc_refl_coeffs=True)
        self.assertEqual(params["reflA"], -100)
        self.assertEqual(params["reflB"], -100)
        params = _prepare_params_for_task(2, { }, calc_refl_coeffs=True)
        self.assertTrue("reflA" in params)
        self.assertEqual(params["reflA"], -100)
        self.assertTrue("reflB" in params)
        self.assertEqual(params["reflB"], -100)

    def test__prepare_params_for_task_task3_calc_refl_coeffs_true(self):
        """ Test _prepare_params_for_task(task=3, calc_refl_coeffs=True) check ignored """
        params = _prepare_params_for_task(3, { "reflA": 0, "reflB": 0 }, calc_refl_coeffs=True)
        self.assertEqual(params["reflA"], 0)
        self.assertEqual(params["reflB"], 0)

    def test__prepare_params_for_task_in_place_true(self):
        """ Test _prepare_params_for_task(in_place=True) byref params updated """
        # Requesting a fit on rA & rB causes the rA_plus_rB & k params to be
        # changed which is how we detect if the params arg has been modified.
        params = { "rA": 2, "rB": 1, "rA_plus_rB": 3, "k": 0.5 }
        _prepare_params_for_task(2, params, fit_rA_and_rB=True, in_place=True)
        self.assertEqual(params["rA_plus_rB"], -2, "params arg not modified")

    def test__prepare_params_for_task_in_place_false(self):
        """ Test _prepare_params_for_task(in_place=False) byref params unchanged """
        # Requesting a fit on rA & rB causes the rA_plus_rB & k params to be
        # changed which is how we detect if the params arg has been modified.
        params = { "rA": 2, "rB": 1, "rA_plus_rB": 3, "k": 0.5 }
        new_params = _prepare_params_for_task(2, params, fit_rA_and_rB=True, in_place=False)
        self.assertEqual(params["rA_plus_rB"], 3, "params arg has been modified")
        self.assertEqual(new_params["rA_plus_rB"], -2, "return params unchanged")

if __name__ == "__main__":
    unittest.main()