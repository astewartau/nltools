import os
import numpy as np
import nibabel as nb
import pandas as pd
import glob
from nltools.simulator import Simulator
from nltools.data import Brain_Data, Adjacency
from nltools.data import threshold
from nltools.mask import create_sphere
from sklearn.metrics import pairwise_distances
import matplotlib
matplotlib.use('TkAgg')

def test_brain_data(tmpdir):
    sim = Simulator()
    r = 10
    sigma = 1
    y = [0, 1]
    n_reps = 3
    output_dir = str(tmpdir)
    sim.create_data(y, sigma, reps=n_reps, output_dir=output_dir)

    shape_3d = (91, 109, 91)
    shape_2d = (6, 238955)
    y=pd.read_csv(os.path.join(str(tmpdir.join('y.csv'))),header=None,index_col=None).T
    flist = glob.glob(str(tmpdir.join('centered*.nii.gz')))
    
    # Test load list
    dat = Brain_Data(data=flist,Y=y)

    # Test load file
    assert Brain_Data(flist[0])

    # Test to_nifti
    d = dat.to_nifti()
    assert d.shape[0:3] == shape_3d

    # Test load nibabel
    assert Brain_Data(d)

    # Test shape
    assert dat.shape() == shape_2d

    # Test Mean
    assert dat.mean().shape()[0] == shape_2d[1]

    # Test Std
    assert dat.std().shape()[0] == shape_2d[1]

    # Test add
    new = dat + dat
    assert new.shape() == shape_2d

    # Test subtract
    new = dat - dat
    assert new.shape() == shape_2d

    # Test multiply
    new = dat * dat
    assert new.shape() == shape_2d

    # Test Iterator
    x = [x for x in dat]
    assert len(x)==len(dat)
    assert len(x[0].data.shape)==1

    # # Test T-test
    out = dat.ttest()
    assert out['t'].shape()[0]==shape_2d[1]

    # # # Test T-test - permutation method
    # out = dat.ttest(threshold_dict={'permutation':'tfce','n_permutations':50,'n_jobs':1})
    # assert out['t'].shape()[0]==shape_2d[1]

    # Test Regress
    dat.X = pd.DataFrame({'Intercept':np.ones(len(dat.Y)),'X1':np.array(dat.Y).flatten()},index=None)
    out = dat.regress()
    assert out['beta'].shape() == (2,shape_2d[1])

    # Test indexing
    assert out['t'][1].shape()[0] == shape_2d[1]

    # Test threshold
    i=1
    tt = threshold(out['t'][i], out['p'][i], .05)
    assert isinstance(tt,Brain_Data)

    # Test write
    dat.write(os.path.join(str(tmpdir.join('test_write.nii'))))
    assert Brain_Data(os.path.join(str(tmpdir.join('test_write.nii'))))

    # Test append
    assert dat.append(dat).shape()[0]==shape_2d[0]*2

    # Test distance
    distance = dat.distance(method='euclidean')
    assert distance.shape==(shape_2d[0],shape_2d[0])

    # Test predict
    stats = dat.predict(algorithm='svm', cv_dict={'type': 'kfolds','n_folds': 2, 'n':len(dat.Y)}, plot=False,**{'kernel':"linear"})

    # Support Vector Regression, with 5 fold cross-validation with Platt Scaling
    # This will output probabilities of each class
    stats = dat.predict(algorithm='svm', cv_dict=None, plot=False,**{'kernel':'linear','probability':True})

    assert isinstance(stats['weight_map'],Brain_Data)
    # Logistic classificiation, with 5 fold stratified cross-validation.  

    stats = dat.predict(algorithm='logistic', cv_dict={'type': 'kfolds','n_folds': 5, 'n':len(dat.Y)}, plot=False)
    assert isinstance(stats['weight_map'],Brain_Data)

    # Ridge classificiation, with 5 fold between-subject cross-validation, where data for each subject is held out together.
    stats = dat.predict(algorithm='ridgeClassifier', cv_dict=None,plot=False)
    assert isinstance(stats['weight_map'],Brain_Data)

    # Test Similarity
    r = dat.similarity(stats['weight_map'])
    assert len(r)==shape_2d[0]
    r2 = dat.similarity(stats['weight_map'].to_nifti())
    assert len(r2)==shape_2d[0]
    
    # Test apply_mask - might move part of this to test mask suite
    s1 = create_sphere([41, 64, 55], radius=10)
    assert isinstance(s1,nb.Nifti1Image)
    s2 = Brain_Data(s1)
    masked_dat = dat.apply_mask(s1)
    assert masked_dat.shape()[1]==np.sum(s2.data!=0)

    # Test extract_roi
    mask = create_sphere([41, 64, 55], radius=10)
    assert len(dat.extract_roi(mask))==shape_2d[0]

    # Test r_to_z
    z = dat.r_to_z()
    assert z.shape() == dat.shape()

    # Test copy
    d_copy = dat.copy()
    assert d_copy.shape() == dat.shape()

    # Test detrend
    detrend = dat.detrend()
    assert detrend.shape() == dat.shape()

    # # Test Plot
    # dat.plot()
    
    # Test Bootstrap

    # Test multivariate_similarity

def test_adjacency(tmpdir):
    n=10
    sim = np.random.multivariate_normal([0,0,0,0],[[1, 0.8, 0.1, 0.4],
                                         [0.8, 1, 0.6, 0.1],
                                         [0.1, 0.6, 1, 0.3],
                                         [0.4, 0.1, 0.3, 1]],100)
    data = pairwise_distances(sim.T,metric='correlation')
    dat_all = []
    for t in range(n):
        tmp = data
        dat_all.append(tmp)

    dat_single = Adjacency(dat_all[0])
    dat_multiple = Adjacency(dat_all)

    # Test automatic distance/similarity detection
    assert dat_single.matrix_type is 'distance'
    dat_single2 = Adjacency(1-data)
    assert dat_single2.matrix_type is 'similarity'

    # Test length
    assert len(dat_multiple)==dat_multiple.data.shape[0]
    assert len(dat_multiple[0])==1

    # Test Indexing
    assert len(dat_multiple[0]) == 1
    assert len(dat_multiple[0:4]) == 4
    assert len(dat_multiple[0,2,3]) == 3

    # Test copy
    assert np.all(dat_multiple.data==dat_multiple.copy().data)

    # Test squareform & iterable
    if len(dat_multiple) > 1:
        assert len(dat_multiple.squareform())==len(dat_multiple)
    else:
        assert dat_single.squareform().shape==data.shape

    # # Test write
    # dat.write(os.path.join(base_dir,'Analyses','Test.csv'))
    # dat2 = Adjacency(os.path.join(base_dir,'Analyses','Test.csv'))
    # assert np.all(np.isclose(dat.data,dat2.data))

    # Test mean
    assert len(dat_multiple.mean(axis=0))==len(np.mean(dat_multiple.data,axis=0))
    assert len(dat_multiple.mean(axis=1))==len(np.mean(dat_multiple.data,axis=1))

    # Test std
    assert len(dat_multiple.std(axis=1))==len(np.std(dat_multiple.data,axis=1))
    assert len(dat_multiple.std(axis=0))==len(np.std(dat_multiple.data,axis=0))

    # Test similarity
    assert len(dat_multiple.similarity(dat_single.squareform()))==len(dat_multiple)


