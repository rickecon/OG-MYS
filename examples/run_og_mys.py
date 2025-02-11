import multiprocessing
from distributed import Client
import os
import json
import time
import copy
from ogmys.calibrate import Calibration
from ogcore.parameters import Specifications
from ogcore import output_tables as ot
from ogcore import output_plots as op
from ogcore.execute import runner
from ogcore.utils import safe_read_pickle
from ogcore import SS

# SS.ENFORCE_SOLUTION_CHECKS = False


def main():
    # Define parameters to use for multiprocessing
    client = Client()
    num_workers = min(multiprocessing.cpu_count(), 7)
    print("Number of workers = ", num_workers)

    # Directories to save data
    CUR_DIR = os.path.dirname(os.path.realpath(__file__))
    base_dir = os.path.join(CUR_DIR, "OG-MYS-Example", "OUTPUT_BASELINE")
    reform_dir = os.path.join(CUR_DIR, "OG-MYS-Example", "OUTPUT_REFORM")

    """
    ------------------------------------------------------------------------
    Run baseline policy
    ------------------------------------------------------------------------
    """
    # Set up baseline parameterization
    p = Specifications(
        baseline=True,
        num_workers=num_workers,
        baseline_dir=base_dir,
        output_base=base_dir,
    )
    # Update parameters for baseline from default json file
    p.update_specifications(
        json.load(
            open(
                os.path.join(
                    CUR_DIR, "..", "ogmys", "ogmys_default_parameters.json"
                )
            )
        )
    )
    c = Calibration(p, client=client)
    # update tax function parameters in Specifications Object
    d = c.get_dict()
    # additional parameters to change
    updated_params = {
        "omega": d["omega"],
        "g_n_ss": d["g_n_ss"],
        "omega_SS": d["omega_SS"],
        "rho": d["rho"],
        "g_n": d["g_n"],
        "imm_rates": d["imm_rates"],
        "omega_S_preTP": d["omega_S_preTP"],
        "e": d["e"],
    }
    p.update_specifications(updated_params)

    # Run model
    start_time = time.time()
    runner(p, time_path=True, client=client)
    print("run time = ", time.time() - start_time)

    """
    ------------------------------------------------------------------------
    Run reform policy
    ------------------------------------------------------------------------
    """

    # create new Specifications object for reform simulation
    p2 = copy.deepcopy(p)
    p2.baseline = False
    p2.output_base = reform_dir
    # additional parameters to change
    updated_params = {
        "cit_rate": [[0.35]],
    }
    p2.update_specifications(updated_params)
    # Run model
    start_time = time.time()
    runner(p2, time_path=True, client=client)
    print("run time = ", time.time() - start_time)
    client.close()

    """
    ------------------------------------------------------------------------
    Save some results of simulations
    ------------------------------------------------------------------------
    """
    base_tpi = safe_read_pickle(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
    base_params = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
    reform_tpi = safe_read_pickle(
        os.path.join(reform_dir, "TPI", "TPI_vars.pkl")
    )
    reform_params = safe_read_pickle(
        os.path.join(reform_dir, "model_params.pkl")
    )
    ans = ot.macro_table(
        base_tpi,
        base_params,
        reform_tpi=reform_tpi,
        reform_params=reform_params,
        var_list=["Y", "C", "K", "L", "r", "w"],
        output_type="pct_diff",
        num_years=10,
        start_year=base_params.start_year,
    )

    # create plots of output
    op.plot_all(
        base_dir, reform_dir, os.path.join(CUR_DIR, "OG-MYS_example_plots")
    )

    print("Percentage changes in aggregates:", ans)
    # save percentage change output to csv file
    ans.to_csv("ogmys_example_output.csv")


if __name__ == "__main__":
    # execute only if run as a script
    main()
