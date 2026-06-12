transcript on
if {[file exists rtl_work]} {
	vdel -lib rtl_work -all
}
vlib rtl_work
vmap work rtl_work

vlog -vlog01compat -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/escape_coding {C:/Users/wwwde/Documents/Academics/mini project/escape_coding/line_buffer.v}
vlog -vlog01compat -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/escape_decoding {C:/Users/wwwde/Documents/Academics/mini project/escape_decoding/bit_unpacker.v}
vlog -vlog01compat -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/escape_decoding {C:/Users/wwwde/Documents/Academics/mini project/escape_decoding/medrice_decoder.v}
vlog -vlog01compat -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/escape_decoding {C:/Users/wwwde/Documents/Academics/mini project/escape_decoding/medrice_escape_decode.v}

vlog -vlog01compat -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/escape_decoding {C:/Users/wwwde/Documents/Academics/mini project/escape_decoding/medrice_escape_decode.v}
vlog -vlog01compat -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/escape_decoding {C:/Users/wwwde/Documents/Academics/mini project/escape_decoding/medrice_decoder.v}
vlog -vlog01compat -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/escape_decoding {C:/Users/wwwde/Documents/Academics/mini project/escape_decoding/decoder_tb.v}
vlog -vlog01compat -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/escape_decoding {C:/Users/wwwde/Documents/Academics/mini project/escape_decoding/bit_unpacker.v}
vlog -vlog01compat -work work +incdir+C:/Users/wwwde/Documents/Academics/mini\ project/escape_decoding/../escape_coding {C:/Users/wwwde/Documents/Academics/mini project/escape_decoding/../escape_coding/line_buffer.v}

vsim -t 1ps -L altera_ver -L lpm_ver -L sgate_ver -L altera_mf_ver -L altera_lnsim_ver -L cyclonev_ver -L cyclonev_hssi_ver -L cyclonev_pcie_hip_ver -L rtl_work -L work -voptargs="+acc"  decoder_tb

add wave *
view structure
view signals
run -all
