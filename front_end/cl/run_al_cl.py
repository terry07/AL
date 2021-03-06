"""
The :mod:`front_end.cl.run_al_cl` implements the methods needed to
run the command-line interface.
"""
import os, sys
path = os.path.join(os.path.dirname("__file__"), '../..')
sys.path.insert(0, path)



import argparse

from collections import defaultdict
from time import time

from zipfile import ZipFile
import csv

import numpy as np
import matplotlib.pyplot as plt


from sklearn.naive_bayes import MultinomialNB, GaussianNB, BernoulliNB
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.datasets import load_svmlight_file
from sklearn.cross_validation import StratifiedKFold
from sklearn.preprocessing import LabelEncoder

from al.learning_curve import LearningCurve



def load_data(dataset1, dataset2=None, make_dense=False):
    """Loads the dataset(s).
    Can handle zip files.
    If the data file extension is csv, it reads a csv file.
    Then, the last column is treated as the target variable.
    Otherwise, the data files are assumed to be in svmlight/libsvm format.

    **Parameters**

    * dataset1 (*str*) - Path to the file of the first dataset.
    * dataset2 (*str or None*) - If not None, path to the file of second dataset
    * make_dense (*boolean*) - Whether to return dense matrices instead of sparse ones (Note: data from csv files will always be treated as dense)

    **Returns**

    * (X_pool, X_test, y_pool, y_test) - Pool and test files if two files are provided
    * (X, y) - The single dataset

    """
    
    def _get_extensions(dataset1, dataset2):
        first_extension = dataset1[dataset1.rfind('.')+1:]
        second_extension = None
        if dataset2 is not None:
            second_extension = dataset2[dataset2.rfind('.')+1:]
        
        return first_extension, second_extension
    
    # Test if these are zipped files
    
    fe, se = _get_extensions(dataset1, dataset2)
    
    if se and fe != se:
        raise ValueError("Cannot mix and match different file formats")
    
    iz_zip = fe == 'zip'    
    
    # Open the files and test if these are csv    
    dataset1_file = None
    dataset2_file = None    
    is_csv = False    
    
    if iz_zip:
        my_zip_dataset1 = ZipFile(dataset1)
        inside_zip_dataset1 = my_zip_dataset1.namelist()[0] # Assuming each zip contains a single file
        inside_zip_dataset2 = None
        dataset1_file = my_zip_dataset1.open(inside_zip_dataset1)
        if dataset2 is not None:
            my_zip_dataset2 = ZipFile(dataset2)
            inside_zip_dataset2 = my_zip_dataset2.namelist()[0] # Assuming each zip contains a single file
            dataset2_file = my_zip_dataset2.open(inside_zip_dataset2)
        inside_fe, inside_se = _get_extensions(inside_zip_dataset1, inside_zip_dataset2)
        if inside_se and inside_fe != inside_se:
            raise ValueError("Cannot mix and match different file formats")
        
        is_csv = inside_fe == 'csv'
    else:
        
        dataset1_file = open(dataset1, 'r')
        if dataset2 is not None:
            dataset2_file = open(dataset2, 'r')
                 
        is_csv = fe == 'csv'    
            
    if dataset2 is not None:       
        if is_csv:
            X_pool, y_pool = load_csv(dataset1_file)
            X_test, y_test = load_csv(dataset2_file)
        else:
            X_pool, y_pool = load_svmlight_file(dataset1_file)
            _, num_feat = X_pool.shape
            X_test, y_test = load_svmlight_file(dataset2_file, n_features=num_feat)
            if make_dense:
                X_pool = X_pool.todense()
                X_test = X_test.todense()
        
        le = LabelEncoder()
        y_pool = le.fit_transform(y_pool)        
        y_test = le.transform(y_test)
        
        dataset1_file.close()
        dataset2_file.close()
        
        return (X_pool, X_test, y_pool, y_test) 

    else:
        
        if is_csv:
            X, y = load_csv(dataset1_file)
        else:
            X, y = load_svmlight_file(dataset1_file)
            if make_dense:
                X = X.todense()
        
        le = LabelEncoder()
        y = le.fit_transform(y)
        
        dataset1_file.close()
        
        return X, y



def load_csv(dataset_file):
    X=[]
    y=[]
    csvreader = csv.reader(dataset_file, delimiter=',')
    next(csvreader, None)#skip names
    for row in csvreader:
        X.append(row[:-1])
        y.append(row[-1])
    X=np.array(X, dtype=float)    
    y=np.array(y)
    return X, y
    
def save_all_results(file_name, results):
    with open(file_name, 'w') as f:
        bs = sorted(results.keys())
        num_trials = len(results[bs[0]])
        # Header
        f.write("Budget")
        for t in range(num_trials):
            f.write(",Trial"+str(t))
        f.write("\n")
        # Body
        for b in bs:
            f.write(str(b))
            res=results[b]
            for r in res:
                f.write(","+str(r))
            f.write("\n")


def plot_and_save_average_results(results, file_name):
    
    strategies = results.keys()
    
    measures = sorted(results[strategies[0]].keys())
    
    bs = sorted(results[strategies[0]][measures[0]].keys())
    
    for measure in measures:
        plt.figure(1)
        for strategy in strategies:
            ave = [results[strategy][measure][b] for b in bs]
            plt.plot(bs, ave, '-', label=strategy)
        plt.legend(loc='lower right')
        plt.xlabel('Budget')
        plt.ylabel(measure)
        plt.title(measure)
        fig_file_name=file_name +"-" + measure + ".png"
        plt.savefig(fig_file_name, format='png', bbox_inches='tight')
        plt.close(1)
        csv_file_name = file_name + "-" + measure + ".csv"
        with open(csv_file_name, "w") as f:
            f.write("Budget")
            for strategy in strategies:
                f.write(","+strategy)
            f.write("\n")
            for b in bs:
                f.write(str(b))
                for strategy in strategies:
                    f.write(","+str(results[strategy][measure][b]))
                f.write("\n")

def plot_average_results(results):
    
    strategies = results.keys()
    
    measures = sorted(results[strategies[0]].keys())
    
    bs = sorted(results[strategies[0]][measures[0]].keys())
    
    # numrows, numcols, fignum
    
    num_cols = 2
    num_rows = int(np.ceil(len(measures)/2.0))
    
    measure_index=0
    
    plt.figure(1)
    for _ in range(num_rows):
        for _ in range(num_cols):
            plt.subplot(num_rows, num_cols, measure_index+1)
            for strategy in strategies:
                ave = [results[strategy][measures[measure_index]][b] for b in bs]
                plt.plot(bs, ave, '-', label=strategy)
            plt.legend(loc='lower right')
            plt.title(measures[measure_index])
            measure_index += 1
    
    plt.show()
    plt.close(1)

class cmd_parse(object):
    """Class - command line parser"""
    def __init__(self):
        self.parser = argparse.ArgumentParser()

    def retrieve_args(self):
        """Adds arguments to the parser for each respective setting of the command line interface"""
        # Classifier
        self.parser.add_argument("-c","--classifier", choices=['KNeighborsClassifier', 'LogisticRegression', 'SVC', 'BernoulliNB',
                        'DecisionTreeClassifier', 'RandomForestClassifier', 'AdaBoostClassifier', 'GaussianNB', 'MultinomialNB'],
                        default='MultinomialNB', help="Represents the classifier that will be used (default: MultinomialNB) .")

        # Classifier's arguments
        self.parser.add_argument("-a","--arguments", default='',
                        help="Represents the arguments that will be passed to the classifier (default: '').")

        # Data: Testing and training already split
        self.parser.add_argument("-d", '--data', nargs=2, metavar=('pool', 'test'),
                        default=["data/imdb-binary-pool-mindf5-ng11", "data/imdb-binary-test-mindf5-ng11"],
                        help='Files that contain the data, pool and test, and number of features (default: data/imdb-binary-pool-mindf5-ng11 data/imdb-binary-test-mindf5-ng11 27272).')

        # Data: Single File
        self.parser.add_argument("-sd", '--sdata', type=str, default='',
                        help='Single file that contains the data. Cross validation will be performed (default: None).')
        
        # Whether to make the data dense
        self.parser.add_argument('-make_dense', default=False, action='store_true', help='Whether to make the sparse data dense. Some classifiers require this.')
        
        # Number of Folds
        self.parser.add_argument("-cv", type=int, default=10, help="Number of folds for cross validation. Works only if a single dataset is loaded (default: 10).")

        # File: Name of file that will be written the results
        self.parser.add_argument("-f", '--file', type=str, default=None,
                        help='This feature represents the name that will be written with the result. If it is left blank, the file will not be written (default: None ).')

        # Number of Trials
        self.parser.add_argument("-nt", "--num_trials", type=int, default=10, help="Number of trials (default: 10).")

        # Strategies
        self.parser.add_argument("-st", "--strategies", choices=['erreduct', 'loggain', 'qbc', 'rand','unc'], nargs='*',default=['rand'],
                        help="Represent a list of strategies for choosing next samples (default: rand).")

        # Boot Strap
        self.parser.add_argument("-bs", '--bootstrap', default=10, type=int,
                        help='Sets the Boot strap (default: 10).')

        # Budget
        self.parser.add_argument("-b", '--budget', default=500, type=int,
                        help='Sets the budget (default: 500).')

        # Step size
        self.parser.add_argument("-sz", '--stepsize', default=10, type=int,
                        help='Sets the step size (default: 10).')

        # Sub pool size
        self.parser.add_argument("-sp", '--subpool', default=None, type=int,
                        help='Sets the sub pool size (default: None).')


    def assign_args(self):
        """Assigns values to each of the specified command line arguments for use by :mod:`al.learning_curve`"""

        t0 = time()

        self.args = self.parser.parse_args()
        self.classifier = eval((self.args.classifier))
        model_arguments = self.args.arguments.split(',')
        self.alpha = {}

        for argument in model_arguments:
            if argument.find('=') >= 0:
                index, value = argument.split('=')
                self.alpha[index] = eval(value)

        self.num_trials = self.args.num_trials
        self.strategies = self.args.strategies
        self.boot_strap_size = self.args.bootstrap
        self.budget = self.args.budget
        self.step_size = self.args.stepsize
        self.sub_pool = self.args.subpool
        
        self.make_dense = self.args.make_dense
        self.cv = self.args.cv

        self.filename = self.args.file
        self.duration = defaultdict(lambda: 0.0)
        self.accuracies = defaultdict(lambda: [])
        self.aucs = defaultdict(lambda: [])

        if self.args.sdata:
            self.X, self.y = load_data(self.args.sdata, None, self.make_dense)
        else:
            self.X_pool, self.X_test, self.y_pool, self.y_test = load_data(self.args.data[0], self.args.data[1], self.make_dense)

        duration = time() - t0

        print
        print "Loading took %0.2fs." % duration
        print        

    def run_al(self):
        """Calls :mod:`al.learning_curve.LearningCurve` and draws plots using :mod:`utils.utils`"""
        learning_api = LearningCurve()
        # if self.filename:
        #     f = open(self.filename, 'a')
        # else:
        #     f = open('avg_results.txt', 'a')
        
        average_performances = {}
        
        for strategy in self.strategies:
            
            print "Strategy: %s" %strategy
            
            if self.args.sdata:
                performances = None
                skf = StratifiedKFold(self.y, n_folds=self.cv, shuffle=True, random_state=42)
                for pool, test in skf:
                    perfs = learning_api.run_trials(self.X[pool], self.y[pool], self.X[test], self.y[test], strategy, self.classifier, self.alpha, self.boot_strap_size, self.step_size, self.budget, self.num_trials)
                    if performances is None:
                        performances = perfs
                    else: # Merge
                        measures = perfs.keys()
                        bs = perfs[measures[0]].keys()
                        for measure in measures:
                            for b in bs:
                                performances[measure][b] += perfs[measure][b]                        
            else:
                performances = learning_api.run_trials(self.X_pool, self.y_pool, self.X_test, self.y_test, strategy, self.classifier, self.alpha, self.boot_strap_size, self.step_size, self.budget, self.num_trials)
            
            measures = performances.keys()
            
            bs = sorted(performances[measures[0]].keys())
            
            average_performances[strategy] = {}
            
            for measure in measures:
                
                average_performances[strategy][measure] = {}
                for b in bs:
                    average_performances[strategy][measure][b] = np.mean(performances[measure][b])         
            
                if self.filename is not None:
                    file_name = self.filename + "_" + strategy + "_" + measure +"_all.csv"
                    save_all_results(file_name, performances[measure])
                
                
        
        plot_and_save_average_results(average_performances, self.filename)
        #plot_average_results(average_performances)

    def main(self):
        """Calls :mod:`retrieve_args`, :mod:`assign_args`, :mod:`run_al`"""
        self.retrieve_args()
        self.assign_args()
        self.run_al()

if __name__ == '__main__':
    cli_app = cmd_parse()
    cli_app.main()
