

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Long.hashCode(input_1_0);
        Integer output_2 = Long.hashCode(input_2_0);

        
        // Compare output
        if (output_1 == 732938541 && output_2 == -1309678219) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

