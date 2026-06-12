transcript on
if {[file exists rtl_work]} {
	vdel -lib rtl_work -all
}
vlib rtl_work
vmap work rtl_work

vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/pixel_in.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/line_buffer.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/med_predictor.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/residual_gen.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/bit_packer.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/output_writer.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/signed_mapper.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/k_estimator.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/rice_encoder.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/med_rice.sv}

vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/bit_packer.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/k_estimator.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/line_buffer.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/med_predictor.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/med_rice.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/med_rice_tb.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/output_writer.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/pixel_in.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/residual_gen.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/rice_encoder.sv}
vlog -sv -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/verilog\ codes {C:/Users/wwwde/Documents/Academics/mini project/verilog codes/signed_mapper.sv}

vsim -t 1ps -L altera_ver -L lpm_ver -L sgate_ver -L altera_mf_ver -L altera_lnsim_ver -L cyclonev_ver -L cyclonev_hssi_ver -L cyclonev_pcie_hip_ver -L rtl_work -L work -voptargs="+acc"  med_rice_tb

add wave *
view structure
view signals
run -all
