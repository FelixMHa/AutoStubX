

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Long.hashCode(input_1_0);
        Integer output_2 = Long.hashCode(input_2_0);

        
        // Compare output
        if (output_1 == 39683100 && output_2 == 989006759) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

