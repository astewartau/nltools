import numpy as np
import pandas as pd
from nltools.data import Design_Matrix
from nltools.external.hrf import glover_hrf
import pytest


def test_add_poly(sim_design_matrix):
    matp = sim_design_matrix.add_poly(2)
    assert matp.shape[1] == 7
    assert sim_design_matrix.add_poly(2, include_lower=False).shape[1] == 5


def test_add_dct_basis(sim_design_matrix):
    matpd = sim_design_matrix.add_dct_basis()
    assert matpd.shape[1] == 15


def test_vif(sim_design_matrix):
    matpd = sim_design_matrix.add_poly(2).add_dct_basis()
    assert all(matpd.vif() < 2.0)
    assert not all(matpd.vif(exclude_polys=False) < 2.0)
    matc = matpd.clean()
    assert matc.shape[1] == 16


def test_convolve(sim_design_matrix):
    TR = 2.0
    assert sim_design_matrix.convolve().shape == sim_design_matrix.shape
    hrf = glover_hrf(TR, oversampling=1.0)
    assert (
        sim_design_matrix.convolve(conv_func=np.column_stack([hrf, hrf])).shape[1]
        == sim_design_matrix.shape[1] + 4
    )


def test_zscore(sim_design_matrix):
    matz = sim_design_matrix.zscore(columns=["face_A", "face_B"])
    assert (
        (matz[["house_A", "house_B"]] == sim_design_matrix[["house_A", "house_B"]])
        .all()
        .all()
    )


def test_replace(sim_design_matrix):
    assert (
        sim_design_matrix.replace_data(np.zeros((500, 4))).shape
        == sim_design_matrix.shape
    )


def test_upsample(sim_design_matrix):
    newTR = 1.0
    target = 1.0 / newTR
    assert (
        sim_design_matrix.upsample(target).shape[0]
        == sim_design_matrix.shape[0] * 2 - target * 2
    )


def test_downsample(sim_design_matrix):
    newTR = 4.0
    target = 1.0 / newTR
    assert (
        sim_design_matrix.downsample(target).shape[0] == sim_design_matrix.shape[0] / 2
    )


def test_append(sim_design_matrix):
    mats = sim_design_matrix.append(sim_design_matrix)
    assert mats.shape[0] == sim_design_matrix.shape[0] * 2
    # Keep polys separate by default

    assert (mats.shape[1] - 4) == (sim_design_matrix.shape[1] - 4) * 2
    # Otherwise stack them
    mats = sim_design_matrix.append(sim_design_matrix, keep_separate=False)
    assert mats.shape[1] == sim_design_matrix.shape[1]
    assert mats.shape[0] == sim_design_matrix.shape[0] * 2

    # Keep a single stimulus column separate
    assert (
        sim_design_matrix.append(sim_design_matrix, unique_cols=["face_A"]).shape[1]
        == 5
    )

    # Keep a common stimulus class separate
    assert (
        sim_design_matrix.append(sim_design_matrix, unique_cols=["face*"]).shape[1] == 6
    )
    # Keep a common stimulus class and a different single stim separate
    assert (
        sim_design_matrix.append(
            sim_design_matrix, unique_cols=["face*", "house_A"]
        ).shape[1]
        == 7
    )
    # Keep multiple stimulus class separate
    assert (
        sim_design_matrix.append(
            sim_design_matrix, unique_cols=["face*", "house*"]
        ).shape[1]
        == 8
    )

    # Growing a multi-run design matrix; keeping things separate
    num_runs = 4
    all_runs = Design_Matrix(sampling_freq=0.5)
    for i in range(num_runs):
        run = Design_Matrix(
            np.array(
                [
                    [1, 0, 0, 0],
                    [1, 0, 0, 0],
                    [0, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 0],
                    [0, 0, 0, 1],
                    [0, 0, 0, 1],
                ]
            ),
            sampling_freq=0.5,
            columns=["stim_A", "stim_B", "cond_C", "cond_D"],
        )
        run = run.add_poly(2)
        all_runs = all_runs.append(run, unique_cols=["stim*", "cond*"])
    assert all_runs.shape == (44, 28)


def test_clean(sim_design_matrix):
    # Drop correlated column
    corr_cols = sim_design_matrix.assign(new_col=lambda df: df.iloc[:, 0])
    out = corr_cols.clean(verbose=True)
    assert out.shape[1] < corr_cols.shape[1]

    # Test for bug #413 about args combinations
    out = corr_cols.clean(fill_na=None, exclude_polys=True, verbose=True)
    assert out.shape[1] < corr_cols.shape[1]

    # Raise an error if try to clean with an input matrix that has duplicate column names
    dup_cols = pd.concat([sim_design_matrix, sim_design_matrix], axis=1)
    with pytest.raises(ValueError):
        _ = dup_cols.clean()
