

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Character.toUpperCase(input_1_0);
        Integer output_2 = Character.toUpperCase(input_2_0);

        
        // Compare output
        if (output_1 == 46816 && output_2 == 0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

