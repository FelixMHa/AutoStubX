

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_1_1 = Double.valueOf(args[1]);
        Double input_2_0 = Double.valueOf(args[2]);
        Double input_2_1 = Double.valueOf(args[3]);


        // Perform computation         
        Integer output_1 = Double.compare(input_1_0, input_1_1);
        Integer output_2 = Double.compare(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == -1 && output_2 == 1) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

