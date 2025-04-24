

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Double.hashCode(input_1_0);
        Integer output_2 = Double.hashCode(input_2_0);

        
        // Compare output
        if (output_1 == 881452966 && output_2 == -1459504296) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

