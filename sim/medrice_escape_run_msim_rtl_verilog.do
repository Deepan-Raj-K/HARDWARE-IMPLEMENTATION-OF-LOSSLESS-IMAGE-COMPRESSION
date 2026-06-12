transcript on
if {[file exists rtl_work]} {
	vdel -lib rtl_work -all
}
vlib rtl_work
vmap work rtl_work

vlog -vlog01compat -work work +incdir+F:/Documents/Academics/mini\ project/escape_coding {F:/Documents/Academics/mini project/escape_coding/medrice_escape_encoder.v}

vlog -vlog01compat -work work +incdir+F:/Documents/Academics/mini\ project/escape_coding {F:/Documents/Academics/mini project/escape_coding/tb_encoder.v}
vlog -vlog01compat -work work +incdir+F:/Documents/Academics/mini\ project/escape_coding {F:/Documents/Academics/mini project/escape_coding/medrice_escape_encoder.v}

vsim -t 1ps -L altera_ver -L lpm_ver -L sgate_ver -L altera_mf_ver -L altera_lnsim_ver -L cyclonev_ver -L cyclonev_hssi_ver -L cyclonev_pcie_hip_ver -L rtl_work -L work -voptargs="+acc"  tb_encoder

add wave *
view structure
view signals
run -all
